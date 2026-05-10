// Lab interface module - handles protocol and report generation

interface Export {
  id: string;
  type: string;
  filename: string;
  createdAt: string;
}

// In-memory storage for demo purposes
const exports: Export[] = [];

// Generate SiLA 2 protocol
export function generateProtocol(taskId: string, type: string): any {
  const protocolId = `protocol-${Date.now()}`;
  const filename = `${type}-protocol-${taskId.slice(-8)}.xml`;

  // Generate mock XML content
  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<SiLAProtocol version="2.0">
  <Header>
    <Title>${type} Protocol</Title>
    <CreatedBy>BioDockify AI</CreatedBy>
    <TaskId>${taskId}</TaskId>
    <CreatedAt>${new Date().toISOString()}</CreatedAt>
  </Header>
  <Steps>
    <Step id="1">
      <Command>Initialize</Command>
      <Description>Prepare ${type} system</Description>
      <Parameters>
        <Parameter name="Temperature" value="22°C" />
        <Parameter name="Humidity" value="45%" />
      </Parameters>
    </Step>
    <Step id="2">
      <Command>Load Reagents</Command>
      <Description>Load required reagents into system</Description>
    </Step>
    <Step id="3">
      <Command>Execute Protocol</Command>
      <Description>Run ${type} protocol steps</Description>
    </Step>
    <Step id="4">
      <Command>Cleanup</Command>
      <Description>Cleanup and calibrate system</Description>
    </Step>
  </Steps>
</SiLAProtocol>`;

  // Store export record
  exports.push({
    id: protocolId,
    type: 'SiLA 2 Protocol',
    filename,
    createdAt: new Date().toISOString(),
  });

  return {
    url: `/api/v1/lab/exports/${protocolId}`,
    filename,
    content: xmlContent,
  };
}

// Generate research report
export function generateReport(taskId: string, template: string): any {
  const reportId = `report-${Date.now()}`;
  const filename = `research-report-${template}-${taskId.slice(-8)}.docx`;

  // Store export record
  exports.push({
    id: reportId,
    type: `${template} Report`,
    filename,
    createdAt: new Date().toISOString(),
  });

  return {
    url: `/api/v1/lab/exports/${reportId}`,
    filename,
  };
}

// Get recent exports
export function getRecentExports(): any[] {
  return exports
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 10);
}
