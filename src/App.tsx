import { useState, useEffect, useRef } from 'react';
import { ThemeProvider, useTheme } from 'next-themes';
import {
  Upload,
  Play,
  Pause,
  Square,
  RotateCcw,
  Download,
  Search,
  FileText,
  BarChart3,
  Clock,
  Zap,
  AlertCircle,
  CheckCircle2,
  XCircle,
  TestTube,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { api, createWebSocket } from '@/services/api';
import type { ProcessingStats, ClassificationResult, MetadataRecord, LogEntry, ParserTestResult } from '@/types';
import { formatDuration, formatNumber } from '@/hooks/useProcessing';

const initialStats: ProcessingStats = {
  total_files_found: 0,
  files_processed: 0,
  files_remaining: 0,
  valid_records: 0,
  cancelled_records: 0,
  files_with_errors: 0,
  unique_systems: 0,
  elapsed_seconds: 0,
  estimated_remaining_seconds: 0,
  files_per_second: 0,
  status: 'pending',
  current_file: '',
  current_system: '',
  current_status: '',
};

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="ml-auto"
    >
      {theme === 'dark' ? 'Light' : 'Dark'}
    </Button>
  );
}


function StatCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground truncate">{title}</p>
            <p className="text-xl font-semibold truncate">{value}</p>
            {description && <p className="text-[10px] text-muted-foreground truncate">{description}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProcessingDashboard() {
  const [stats, setStats] = useState<ProcessingStats>(initialStats);
  const [classifications, setClassifications] = useState<ClassificationResult[]>([]);
  const [records, setRecords] = useState<MetadataRecord[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [parserTestResult, setParserTestResult] = useState<ParserTestResult | null>(null);
  const [parserTestLoading, setParserTestLoading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const parserTestInputRef = useRef<HTMLInputElement>(null);
  const reconnectTimer = useRef<number | null>(null);
  const connectWebSocket = () => {
  console.log("[App] Connecting WebSocket...");

  wsRef.current = createWebSocket((data) => {
    const msg = data as {
      type: string;
      data: ProcessingStats;
    };

    if (msg.type === "progress" || msg.type === "init") {
      setStats(msg.data);

      if (msg.data.status === "running") {
        setIsProcessing(true);
      } else if (
        msg.data.status === "completed" ||
        msg.data.status === "cancelled" ||
        msg.data.status === "error"
      ) {
        setIsProcessing(false);
      }
    }
  });

  wsRef.current.onopen = () => {
    console.log("[WS] Connected");
    setWsConnected(true);
  };

  wsRef.current.onclose = () => {
    console.log("[WS] Disconnected");
    setWsConnected(false);

    reconnectTimer.current = window.setTimeout(() => {
      connectWebSocket();
    }, 2000);
  };
};

  // Initialize WebSocket
  useEffect(() => {
  connectWebSocket();

  return () => {
    wsRef.current?.close();

    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
  };
}, []);

  // Fetch classifications when processing completes
  useEffect(() => {
    if (stats.status === 'completed') {
      fetchClassifications();
      fetchRecords();
      fetchLogs();
    }
  }, [stats.status]);

  const fetchClassifications = async () => {
    try {
      const data = await api.getClassifications();
      setClassifications(data.classifications);
    } catch (e) {
      console.error('Failed to fetch classifications:', e);
    }
  };
  const fetchRecords = async () => {
  try {
    const data = await api.getRecords();
    setRecords(data.records);
  } catch (e) {
    console.error("Failed to fetch records:", e);
  }
};

  const fetchLogs = async () => {
    try {
      const data = await api.getLogs();
      setLogs(data.entries);
    } catch (e) {
      console.error('Failed to fetch logs:', e);
    }
  };


  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.zip')) {
      toast.error('Please upload a ZIP file');
      return;
    }

    setIsProcessing(true);
    

    try {
      const result = await api.processZip(file);
      toast.success(`Processed ${result.valid_records} records from ${file.name}`);
    } catch (error) {
      toast.error(`Processing failed: ${error}`);
      setIsProcessing(false);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePause = async () => {
    try {
      await api.pause();
      toast.info('Processing paused');
    } catch (e) {
      toast.error('Failed to pause processing');
    }
  };

  const handleResume = async () => {
    try {
      await api.resume();
      toast.success('Processing resumed');
    } catch (e) {
      toast.error('Failed to resume processing');
    }
  };

  const handleCancel = async () => {
    try {
      await api.cancel();
      toast.warning('Processing cancelled');
      setIsProcessing(false);
    } catch (e) {
      toast.error('Failed to cancel processing');
    }
  };

  const handleReset = async () => {
  try {
    await api.reset();

    setStats(initialStats);
    setClassifications([]);
    setLogs([]);
   

    // Clear parser test
    setParserTestResult(null);
    setParserTestLoading(false);

    if (parserTestInputRef.current) {
      parserTestInputRef.current.value = "";
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

   
    toast.success("Session reset");
  } catch (e) {
    toast.error("Failed to reset session");
  }
};

  const handleExportExcel = async () => {
  if (stats.status !== "completed") {
    toast.error("No data to export. Process files first.");
    return;
  }

  window.location.href = api.exportExcel();

 
};

  const handleExportLogs = (format: 'json' | 'csv') => {
    const link = document.createElement("a");
    link.href = api.exportLogs(format);
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
  };

  const handleParserTest = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.js')) {
      toast.error('Please upload a .js file for parser testing');
      return;
    }

    setParserTestLoading(true);
    setParserTestResult(null);

    try {
      const result = await api.testParser(file);
      setParserTestResult(result);
      toast.success(`Parser test completed: ${result.parser_status}`);
    } catch (error) {
      toast.error(`Parser test failed: ${error}`);
    } finally {
      setParserTestLoading(false);
    }

    if (parserTestInputRef.current) {
      parserTestInputRef.current.value = '';
    }
  };

  const progress = stats.total_files_found > 0
    ? (stats.files_processed / stats.total_files_found) * 100
    : 0;

  const filteredClassifications = classifications.filter((c) =>
    c.sys_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <img
               src="/logo.png"
               alt="JavaScript Metadata Classification System"
               className="h-8 w-8"
             />
            <h1 className="text-xl font-bold">JavaScript Metadata Classifier</h1>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={wsConnected ? 'default' : 'secondary'} className="text-xs">
              {(() => { console.log('[App] Badge render, wsConnected:', wsConnected); return wsConnected ? 'Connected' : 'Disconnected'; })()}
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container px-4 py-6 space-y-6">
        {/* Control Panel */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Control Panel
            </CardTitle>
            <CardDescription>
              Upload a ZIP archive containing JavaScript metadata files to begin classification
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <input
                type="file"
                accept=".zip"
                onChange={handleFileUpload}
                ref={fileInputRef}
                className="hidden"
                id="zip-upload"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing && stats.status === 'running'}
                className="gap-2"
              >
                <Upload className="h-4 w-4" />
                Upload ZIP
              </Button>

              {stats.status === 'running' && (
                <Button variant="outline" onClick={handlePause} className="gap-2">
                  <Pause className="h-4 w-4" />
                  Pause
                </Button>
              )}

              {stats.status === 'paused' && (
                <Button variant="outline" onClick={handleResume} className="gap-2">
                  <Play className="h-4 w-4" />
                  Resume
                </Button>
              )}

              {(stats.status === 'running' || stats.status === 'paused') && (
                <Button variant="destructive" onClick={handleCancel} className="gap-2">
                  <Square className="h-4 w-4" />
                  Cancel
                </Button>
              )}

              <Button
                variant="outline"
                onClick={handleExportExcel}
                disabled={stats.status !== 'completed'}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export Excel
              </Button>

              <Button variant="outline" onClick={handleReset} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
            </div>

            {/* Progress Bar */}
            {stats.total_files_found > 0 && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>{formatNumber(stats.files_processed)} / {formatNumber(stats.total_files_found)} files</span>
                  <span>{progress.toFixed(1)}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            {/* Current Activity */}
            {stats.current_file && (
              <div className="flex items-center gap-4 p-3 bg-muted/50 rounded-lg text-sm">
                <span className="text-muted-foreground">Processing:</span>
                <span className="font-medium truncate max-w-md">{stats.current_file}</span>
                {stats.current_system && (
                  <>
                    <Separator orientation="vertical" className="h-4" />
                    <Badge variant="outline">{stats.current_system}</Badge>
                  </>
                )}
                {stats.current_status && (
                  <>
                    <Separator orientation="vertical" className="h-4" />
                    <span className="text-muted-foreground">{stats.current_status}</span>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Statistics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard
            title="Total Files"
            value={formatNumber(stats.total_files_found)}
            icon={FileText}
          />
          <StatCard
            title="Files Processed"
            value={formatNumber(stats.files_processed)}
            icon={CheckCircle2}
            description={`${formatNumber(stats.files_remaining)} remaining`}
          />
          <StatCard
            title="Valid Records"
            value={formatNumber(stats.valid_records)}
            icon={CheckCircle2}
          />
          <StatCard
            title="Cancelled Records"
            value={formatNumber(stats.cancelled_records)}
            icon={XCircle}
            description="Status = Cancel"
          />
          <StatCard
            title="Files With Errors"
            value={formatNumber(stats.files_with_errors)}
            icon={AlertCircle}
          />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            title="Unique Systems"
            value={formatNumber(stats.unique_systems)}
            icon={BarChart3}
          />
          <StatCard
            title="Elapsed Time"
            value={formatDuration(stats.elapsed_seconds)}
            icon={Clock}
          />
          <StatCard
            title="Remaining Time"
            value={formatDuration(stats.estimated_remaining_seconds)}
            icon={Clock}
          />
          <StatCard
            title="Processing Speed"
            value={`${stats.files_per_second.toFixed(1)} files/s`}
            icon={Zap}
          />
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="classifications" className="space-y-4">
          <TabsList>
            <TabsTrigger value="classifications" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              Classifications
            </TabsTrigger>
            <TabsTrigger value="activity" className="gap-2">
              <Zap className="h-4 w-4" />
              Activity Log
            </TabsTrigger>
            <TabsTrigger value="errors" className="gap-2">
              <AlertCircle className="h-4 w-4" />
              Errors ({logs.filter((l) => l.status === 'error').length})
            </TabsTrigger>
            <TabsTrigger value="parser-test" className="gap-2">
              <TestTube className="h-4 w-4" />
              Parser Test
            </TabsTrigger>
          </TabsList>

          <TabsContent value="classifications" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Classification Results</CardTitle>
                    <CardDescription>
                      {formatNumber(classifications.length)} unique systems found
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search systems..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-64"
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {classifications.length === 0 ? (
                  <div className="py-12 text-center text-muted-foreground">
                    {stats.status === 'completed'
                      ? 'No valid records found'
                      : 'Upload and process files to see classification results'}
                  </div>
                ) : (
                  <ScrollArea className="h-[500px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Sys Name</TableHead>
                          <TableHead className="text-right">Valid Records</TableHead>
                          <TableHead className="w-[340px]">Status Summary</TableHead>
                          <TableHead className="w-[450px]">Unique Note UNIDs</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredClassifications.map((c) => (
                                  <TableRow key={c.sys_name}>
                          <TableCell className="font-medium">
                            {c.sys_name}
                          </TableCell>

                          <TableCell className="text-right">
                            {formatNumber(c.valid_records)}
                          </TableCell>

                          <TableCell className="align-top text-sm leading-6 whitespace-normal break-words max-w-[340px]">
                                {c.status_summary
                                  ? c.status_summary.split(", ").map((s, i) => (
                                      <div key={i}>{s}</div>
                                    ))
                                  : "-"}
                          </TableCell>
                          

                          <TableCell className="max-w-[450px] text-sm whitespace-normal break-words">

                            {Object.keys(c.status_note_map).length > 0 ? (
                          
                              Object.entries(c.status_note_map).map(([status, ids]) => (
                          
                                <div key={status} className="mb-3">
                          
                                  <div className="text-muted-foreground">
                                    {status}
                                  </div>
                          
                                  {ids.map((id) => (
                                    <div key={id} className="ml-3">
                                      • {id}
                                    </div>
                                  ))}
                          
                                </div>
                          
                              ))
                          
                            ) : (
                          
                              "-"
                          
                            )}
                          
                          </TableCell>
                        </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="activity" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Activity Log</CardTitle>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExportLogs('json')}
                    >
                      Export JSON
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExportLogs('csv')}
                    >
                      Export CSV
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  {logs.length === 0 ? (
  <div className="py-12 text-center text-muted-foreground">
    No activity available
  </div>
) : (
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Time</TableHead>
        <TableHead>File</TableHead>
        <TableHead>Processing</TableHead>
        <TableHead>Status</TableHead>
        <TableHead>Outcome</TableHead>
        <TableHead>Reason</TableHead>
      </TableRow>
    </TableHeader>

    <TableBody>
      {logs
        .slice()
        .reverse()
        .map((log, i) => (
          <TableRow key={i}>
            <TableCell className="text-xs text-muted-foreground">
              {new Date(log.timestamp).toLocaleTimeString()}
            </TableCell>

            <TableCell className="font-mono text-xs">
              {log.file_name}
            </TableCell>

            <TableCell>
              <Badge variant="outline">
                {log.action}
              </Badge>
            </TableCell>

            <TableCell>
              <Badge
                variant={
                  log.status === "error"
                    ? "destructive"
                    : log.status === "success"
                    ? "default"
                    : "secondary"
                }
              >
                {log.status}
              </Badge>
            </TableCell>

            <TableCell>
              {log.result || "-"}
            </TableCell>

            <TableCell className="text-sm">
              {log.reason || log.error_message || "-"}
            </TableCell>
          </TableRow>
        ))}
    </TableBody>
  </Table>
)}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="errors" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Error Log</CardTitle>
                <CardDescription>
                  {formatNumber(logs.filter((l) => l.status === 'error').length)} errors encountered
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  {logs.filter((l) => l.status === 'error').length === 0 ? (
                    <div className="py-12 text-center text-muted-foreground">
                      No errors encountered
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Time</TableHead>
                          <TableHead>File</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead>Error Message</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {logs
                          .filter((l) => l.status === 'error')
                          .slice(0, 500)
                          .map((l, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-xs text-muted-foreground">
                                {new Date(l.timestamp).toLocaleTimeString()}
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {l.file_name}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">{l.action}</Badge>
                              </TableCell>
                              <TableCell className="text-red-600 dark:text-red-400 text-sm">
                                {l.error_message}
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="parser-test" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Parser Test Mode</CardTitle>
                    <CardDescription>
                      Validate parser correctness with individual .js files before batch processing
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <input
                  type="file"
                  accept=".js"
                  onChange={handleParserTest}
                  ref={parserTestInputRef}
                  className="hidden"
                  id="parser-test-upload"
                />
                <div className="flex items-center gap-3">
                  <Button
                    onClick={() => parserTestInputRef.current?.click()}
                    disabled={parserTestLoading}
                    className="gap-2"
                  >
                    <TestTube className="h-4 w-4" />
                    {parserTestLoading ? 'Testing...' : 'Select .js File to Test'}
                  </Button>
                </div>

                {/* Parser Test Results */}
                {parserTestResult && (
                  <div className="border rounded-lg p-4 space-y-4">
                    {/* Status Header */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Parser Status</span>
                      <Badge
                        variant={parserTestResult.parser_status === 'PASS' ? 'default' : 'destructive'}
                        className="text-sm"
                      >
                        {parserTestResult.parser_status === 'PASS' ? (
                          <CheckCircle2 className="h-4 w-4 mr-1" />
                        ) : (
                          <XCircle className="h-4 w-4 mr-1" />
                        )}
                        {parserTestResult.parser_status}
                      </Badge>
                    </div>

                    <Separator />

                    {/* Extracted Values */}
                    <div className="grid gap-3">
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <span className="text-muted-foreground">File Name:</span>
                        <span className="col-span-2 font-mono truncate">{parserTestResult.file_name}</span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <span className="text-muted-foreground">note_unid:</span>
                        <span className={`col-span-2 font-mono ${parserTestResult.details.note_unid_found ? '' : 'text-red-500'}`}>
                          {parserTestResult.note_unid || '(NOT FOUND)'}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <span className="text-muted-foreground">sys_name:</span>
                        <span className={`col-span-2 font-mono ${parserTestResult.details.sys_name_found ? '' : 'text-red-500'}`}>
                          {parserTestResult.sys_name || '(NOT FOUND)'}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <span className="text-muted-foreground">status:</span>
                        <span className={`col-span-2 font-mono ${parserTestResult.details.status_found ? '' : 'text-red-500'}`}>
                          {parserTestResult.status || '(NOT FOUND)'}
                        </span>
                      </div>
                    </div>

                    {/* Missing Fields */}
                    {parserTestResult.missing_fields.length > 0 && (
                      <>
                        <Separator />
                        <div className="space-y-2">
                          <span className="text-sm font-medium text-destructive">Missing Fields:</span>
                          <div className="space-y-1">
                            {parserTestResult.missing_fields.map((field, i) => (
                              <div key={i} className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                                <XCircle className="h-4 w-4" />
                                {field}
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {!parserTestResult && !parserTestLoading && (
                  <div className="py-12 text-center text-muted-foreground">
                    Upload a .js file to test the parser
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t py-4 mt-8">
        <div className="container px-4 text-center text-sm text-muted-foreground">
          JavaScript Metadata Classification System v3.0
        </div>
      </footer>

      <Toaster />
    </div>
  );
}

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <ProcessingDashboard />
    </ThemeProvider>
  );
}

export default App;
