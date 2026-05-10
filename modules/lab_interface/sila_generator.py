"""
SiLA 2 Protocol Generator
Generates XML protocols for physical lab automation (Liquid Handlers).
"""

import uuid
from typing import Dict, Any, List

class SiLAGenerator:
    """Base class for SiLA Protocol Generation."""
    
    def generate_protocol(self, research_data: Dict[str, Any]) -> str:
        """
        Generate a SiLA 2 compliant XML protocol string.
        Args:
            research_data: Dictionary containing 'entities' (liquids) and steps.
        """
        raise NotImplementedError

class LiquidHandlerSiLA(SiLAGenerator):
    """Generator for standard Liquid Handling Robots."""
    
    def generate_protocol(self, research_data: Dict[str, Any]) -> str:
        protocol_id = str(uuid.uuid4())
        drugs = research_data.get('entities', {}).get('drugs', [])
        
        # Simple template for a Dispense command
        xml_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<SiLA2Protocol id="{protocol_id}" version="1.0">',
            f'  <Metadata>',
            f'    <Name>BioDockify Auto-Generated Protocol</Name>',
            f'    <Description>Dispense protocol for identified candidates</Description>',
            f'  </Metadata>',
            f'  <Commands>'
        ]
        
        for i, drug in enumerate(drugs):
            # Simulate dispensing 10uL of each drug candidate into a well
            well_id = f"A{i+1}" 
            xml_parts.append(
                f'    <Command name="Dispense">',
            )
            xml_parts.append(f'      <Parameter name="LiquidName">{drug}</Parameter>')
            xml_parts.append(f'      <Parameter name="Volume" unit="uL">10.0</Parameter>')
            xml_parts.append(f'      <Parameter name="TargetWell">{well_id}</Parameter>')
            xml_parts.append(f'    </Command>')
            
        xml_parts.append(f'  </Commands>')
        xml_parts.append(f'</SiLA2Protocol>')
        
        return "\n".join(xml_parts)

if __name__ == "__main__":
    # Test
    gen = LiquidHandlerSiLA()
    print(gen.generate_protocol({"entities": {"drugs": ["Aspirin", "Metformin"]}}))
