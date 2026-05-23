"""Statistics Charts Tool — agent generates publication-quality plots from analysis results."""
from helpers.tool import Tool, Response


class StatisticsChartsTool(Tool):
    async def execute(self, action: str = "chart", **kwargs):
        if action == "chart":
            chart_type = kwargs.get("chart_type", "histogram")
            title = kwargs.get("title", "Chart")

            lines = [f"Statistics Chart: {title}", "=" * 40]
            lines.append(f"Call POST /api/statistics_charts with chart_type={chart_type}")
            lines.append("")
            lines.append("Available chart types:")
            for ct in ["histogram", "boxplot", "scatter", "qq", "bar", "roc", "survival", "correlation_heatmap"]:
                lines.append(f"  - {ct}")
            lines.append("")
            lines.append("The API returns base64 PNG images. Pass your analysis results as values/groups/matrix.")
            return Response(message="\n".join(lines), break_loop=False)

        return Response(
            message="StatisticsCharts actions: chart. Use: StatisticsCharts action=chart chart_type=histogram",
            break_loop=False
        )
