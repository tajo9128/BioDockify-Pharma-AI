### statistics_charts
generate statistical charts: histogram, boxplot, scatter, Q-Q, bar, ROC, survival, heatmap
args: `action` (histogram, boxplot, scatter, qq, bar, roc, survival, heatmap), `data`
optional: `x_column`, `y_column`, `title`, `group_column`
example:
~~~json
{
  "thoughts": ["I need to visualize this data."],
  "headline": "Generating chart",
  "tool_name": "statistics_charts",
  "tool_args": {
    "action": "histogram",
    "data": "[1.2, 1.5, 1.8, 2.1, 2.3]"
  }
}
~~~
