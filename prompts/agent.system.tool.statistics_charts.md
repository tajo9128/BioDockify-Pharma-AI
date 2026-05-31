### statistics_charts
generate statistical charts: histogram, boxplot, scatter, Q-Q, bar, ROC curve, survival curve, correlation heatmap
args:
- `action` (one of: histogram, boxplot, scatter, qq, bar, roc, survival, heatmap)
- `data` (JSON array of data values)
- `x_column`, `y_column` (column names for scatter/boxplot)
- `title` (chart title)
- `group_column` (optional: grouping variable)
returns base64 PNG image
example:
~~~json
{
  "thoughts": ["I need to visualize this data distribution."],
  "headline": "Generating histogram",
  "tool_name": "statistics_charts",
  "tool_args": {
    "action": "histogram",
    "data": "[1.2, 1.5, 1.8, 2.1, 2.3, 2.5, 2.8, 3.0]",
    "title": "Distribution of values"
  }
}
~~~
