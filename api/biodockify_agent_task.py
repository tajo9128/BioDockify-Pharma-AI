from helpers.api import ApiHandler, Request, Response


class ThesisGenerateAgent(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        doc_type = input.get("type", "review")
        topic = input.get("topic", "")
        detail = input.get("detail", "")
        sections = input.get("sections", "")
        references = input.get("references", "")
        include_code = input.get("include_code", False)
        output_format = input.get("output_format", "markdown")

        if not topic:
            return {"content": "Please provide a topic.", "format": output_format}

        prompt = f"""Write a {doc_type} on the following topic.

Topic: {topic}
"""
        if detail:
            prompt += f"Details: {detail}\n"
        if sections:
            prompt += f"Sections to include: {sections}\n"
        if references:
            prompt += f"Key references: {references}\n"
        prompt += f"\nFormat the output as {output_format}."
        if include_code:
            prompt += "\nInclude relevant code examples, equations, or formulas where applicable."

        return {
            "content": prompt,
            "format": output_format,
            "type": doc_type,
            "instruction": "Copy this prompt into chat to generate your document, or type your request directly."
        }
