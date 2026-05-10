"""
SiLA 2 Protocol Generator for BioDockify Lab Interface
Generates XML protocols for liquid handlers and automated lab equipment
"""

from typing import Dict, Any
from datetime import datetime


class LiquidHandlerSiLA:
    """Generate SiLA 2 XML protocols for liquid handlers"""

    def __init__(self):
        self.version = "2.0"
        self.created_by = "BioDockify AI"

    def generate_protocol(self, research_data: Dict[str, Any]) -> str:
        """
        Generate XML protocol from research data

        Args:
            research_data: Dictionary containing research results and metadata

        Returns:
            SiLA 2 XML protocol as string
        """
        title = research_data.get('title', 'Research Protocol')
        task_id = research_data.get('taskId', 'unknown')
        entities = research_data.get('entities', {})

        # Extract relevant entities
        drugs = entities.get('drugs', [])
        proteins = entities.get('proteins', [])
        diseases = entities.get('diseases', [])

        # Build protocol steps dynamically based on research data
        steps_xml = self._build_steps(drugs, proteins, diseases)

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<SiLAProtocol version="{self.version}">
  <Header>
    <Title>{title}</Title>
    <CreatedBy>{self.created_by}</CreatedBy>
    <TaskId>{task_id}</TaskId>
    <CreatedAt>{datetime.now().isoformat()}</CreatedAt>
    <ProtocolType>Liquid Handling</ProtocolType>
  </Header>
  <Metadata>
    <TotalEntities>{len(drugs) + len(proteins) + len(diseases)}</TotalEntities>
    <DrugCount>{len(drugs)}</DrugCount>
    <ProteinCount>{len(proteins)}</ProteinCount>
    <DiseaseCount>{len(diseases)}</DiseaseCount>
  </Metadata>
  <Steps>
    {steps_xml}
  </Steps>
  <Validation>
    <Checksum>auto-generated</Checksum>
    <ValidationStatus>pending</ValidationStatus>
  </Validation>
</SiLAProtocol>'''
        return xml

    def _build_steps(self, drugs: list, proteins: list, diseases: list) -> str:
        """Build protocol steps XML"""
        steps = []

        # Initialization step
        steps.append('''    <Step id="1">
      <Command>Initialize</Command>
      <Description>Prepare liquid handler and calibrate instruments</Description>
      <Parameters>
        <Parameter name="Temperature" value="22°C" />
        <Parameter name="Humidity" value="45%" />
        <Parameter name="LiquidClass" value="Standard" />
      </Parameters>
    </Step>''')

        # Load reagents step
        steps.append('''    <Step id="2">
      <Command>LoadReagents</Command>
      <Description>Load required reagents into deck positions</Description>
      <Parameters>
        <Parameter name="DeckLayout" value="Standard" />
        <Parameter name="Mixing" value="Enabled" />
      </Parameters>
    </Step>''')

        # Generate steps for each drug
        step_id = 3
        for idx, drug in enumerate(drugs[:5]):  # Limit to 5 drugs for demo
            steps.append(f'''    <Step id="{step_id}">
      <Command>PrepareCompound</Command>
      <Description>Prepare {drug} solution</Description>
      <Parameters>
        <Parameter name="CompoundName" value="{drug}" />
        <Parameter name="Concentration" value="1mM" />
        <Parameter name="Volume" value="100uL" />
      </Parameters>
    </Step>''')
            step_id += 1

        # Protein interaction steps
        if proteins:
            steps.append('''    <Step id="{}">
      <Command>MixProteins</Command>
      <Description>Mix protein samples</Description>
      <Parameters>
        <Parameter name="Proteins" value="{}" />
        <Parameter name="MixingTime" value="5min" />
      </Parameters>
    </Step>'''.format(step_id, ', '.join(proteins[:3])))
            step_id += 1

        # Assay step
        steps.append(f'''    <Step id="{step_id}">
      <Command>RunAssay</Command>
      <Description>Execute assay protocol</Description>
      <Parameters>
        <Parameter name="AssayType" value="Binding" />
        <Parameter name="Duration" value="30min" />
        <Parameter name="Readings" value="1min" />
      </Parameters>
    </Step>''')
        step_id += 1

        # Cleanup step
        steps.append(f'''    <Step id="{step_id}">
      <Command>Cleanup</Command>
      <Description>Cleanup instruments and calibrate system</Description>
      <Parameters>
        <Parameter name="WashCycles" value="3" />
        <Parameter name="Decontamination" value="Enabled" />
      </Parameters>
    </Step>''')

        return '\n'.join(steps)

    def generate_crystallization_protocol(self, research_data: Dict[str, Any]) -> str:
        """Generate crystallization protocol XML"""
        title = research_data.get('title', 'Crystallization Protocol')

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<SiLAProtocol version="{self.version}">
  <Header>
    <Title>{title}</Title>
    <CreatedBy>{self.created_by}</CreatedBy>
    <CreatedAt>{datetime.now().isoformat()}</CreatedAt>
    <ProtocolType>Protein Crystallization</ProtocolType>
  </Header>
  <Steps>
    <Step id="1">
      <Command>Initialize</Command>
      <Description>Setup crystallization plates</Description>
    </Step>
    <Step id="2">
      <Command>PrepareScreen</Command>
      <Description>Prepare crystallization screen solutions</Description>
    </Step>
    <Step id="3">
      <Command>Dispense</Command>
      <Description>Dispense protein and solutions</Description>
    </Step>
    <Step id="4">
      <Command>Incubate</Command>
      <Description>Incubate and monitor crystals</Description>
    </Step>
  </Steps>
</SiLAProtocol>'''
        return xml

    def generate_assay_protocol(self, research_data: Dict[str, Any]) -> str:
        """Generate assay protocol XML"""
        title = research_data.get('title', 'Assay Protocol')

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<SiLAProtocol version="{self.version}">
  <Header>
    <Title>{title}</Title>
    <CreatedBy>{self.created_by}</CreatedBy>
    <CreatedAt>{datetime.now().isoformat()}</CreatedAt>
    <ProtocolType>Biochemical Assay</ProtocolType>
  </Header>
  <Steps>
    <Step id="1">
      <Command>Initialize</Command>
      <Description>Initialize plate reader</Description>
    </Step>
    <Step id="2">
      <Command>AddCompounds</Command>
      <Description>Add test compounds to wells</Description>
    </Step>
    <Step id="3">
      <Command>AddSubstrate</Command>
      <Description>Add enzyme substrate</Description>
    </Step>
    <Step id="4">
      <Command>Measure</Command>
      <Description>Measure fluorescence/absorbance</Description>
    </Step>
  </Steps>
</SiLAProtocol>'''
        return xml


# Convenience function
def generate_sila_protocol(research_data: Dict[str, Any], protocol_type: str = 'liquid-handler') -> str:
    """
    Generate SiLA 2 protocol

    Args:
        research_data: Dictionary containing research results
        protocol_type: Type of protocol ('liquid-handler', 'crystallization', 'assay')

    Returns:
        SiLA 2 XML protocol as string
    """
    generator = LiquidHandlerSiLA()

    if protocol_type == 'crystallization':
        return generator.generate_crystallization_protocol(research_data)
    elif protocol_type == 'assay':
        return generator.generate_assay_protocol(research_data)
    else:
        return generator.generate_protocol(research_data)
