# 样式预设详解

paper2html 提供三套视觉主题，满足不同场景需求。

## 主题总览

| 主题 | 关键字 | 背景色 | 强调色 | 适用场景 |
|------|--------|--------|--------|----------|
| 深色实验室 | `dark_lab` | #0f172a | #10b981 | 夜间阅读 |
| 纯净纸张 | `clean_paper` | #ffffff | #3b82f6 | 打印/分享 |
| 霓虹科技 | `neon_tech` | #0c0a1d | #c084fc | 科技展示 |

## CSS 变量对照表

### 深色实验室 (dark_lab)

```css
body.dark_lab {
    /* 背景色 */
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-tertiary: #334155;
    
    /* 文字色 */
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    
    /* 强调色 */
    --accent-primary: #10b981;
    --accent-secondary: #059669;
    --accent-tertiary: #34d399;
    
    /* 语义色 */
    --semantic-abstract-bg: rgba(6, 95, 70, 0.09);
    --semantic-abstract-border: rgba(6, 95, 70, 0.3);
    --semantic-method-bg: rgba(76, 29, 149, 0.09);
    --semantic-method-border: rgba(76, 29, 149, 0.3);
    --semantic-experiment-bg: rgba(21, 94, 40, 0.09);
    --semantic-experiment-border: rgba(21, 94, 40, 0.3);
    --semantic-risk-bg: rgba(127, 29, 29, 0.09);
    --semantic-risk-border: rgba(127, 29, 29, 0.3);
    
    /* 代码 */
    --code-bg: #1e293b;
    --code-border: #334155;
    
    /* 边框 */
    --border-color: #334155;
    --border-radius: 8px;
}
```

### 纯净纸张 (clean_paper)

```css
body.clean_paper {
    /* 背景色 */
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    
    /* 文字色 */
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    
    /* 强调色 */
    --accent-primary: #3b82f6;
    --accent-secondary: #2563eb;
    --accent-tertiary: #60a5fa;
    
    /* 语义色 */
    --semantic-abstract-bg: rgba(6, 95, 70, 0.06);
    --semantic-abstract-border: rgba(6, 95, 70, 0.2);
    --semantic-method-bg: rgba(76, 29, 149, 0.06);
    --semantic-method-border: rgba(76, 29, 149, 0.2);
    --semantic-experiment-bg: rgba(21, 94, 40, 0.06);
    --semantic-experiment-border: rgba(21, 94, 40, 0.2);
    --semantic-risk-bg: rgba(127, 29, 29, 0.06);
    --semantic-risk-border: rgba(127, 29, 29, 0.2);
    
    /* 代码 */
    --code-bg: #f1f5f9;
    --code-border: #e2e8f0;
    
    /* 边框 */
    --border-color: #e2e8f0;
    --border-radius: 6px;
}
```

### 霓虹科技 (neon_tech)

```css
body.neon_tech {
    /* 背景色 */
    --bg-primary: #0c0a1d;
    --bg-secondary: #16113a;
    --bg-tertiary: #221d5c;
    
    /* 文字色 */
    --text-primary: #f5f3ff;
    --text-secondary: #c4b5fd;
    --text-muted: #a78bfa;
    
    /* 强调色 */
    --accent-primary: #c084fc;
    --accent-secondary: #a855f7;
    --accent-tertiary: #e879f9;
    
    /* 语义色 */
    --semantic-abstract-bg: rgba(192, 132, 252, 0.1);
    --semantic-abstract-border: rgba(192, 132, 252, 0.3);
    --semantic-method-bg: rgba(139, 92, 246, 0.1);
    --semantic-method-border: rgba(139, 92, 246, 0.3);
    --semantic-experiment-bg: rgba(34, 197, 94, 0.1);
    --semantic-experiment-border: rgba(34, 197, 94, 0.3);
    --semantic-risk-bg: rgba(239, 68, 68, 0.1);
    --semantic-risk-border: rgba(239, 68, 68, 0.3);
    
    /* 代码 */
    --code-bg: #16113a;
    --code-border: #221d5c;
    
    /* 边框 */
    --border-color: #3b2e7a;
    --border-radius: 8px;
    
    /* 霓虹发光效果 */
    --glow-color: rgba(192, 132, 252, 0.5);
    --glow-spread: 10px;
}
```

## 视觉特征对比

### 深色实验室 (dark_lab)

```
┌────────────────────────────────────────────────────────────┐
│  ██████╗ ███████╗ █████╗ ██████╗  ██████╗  █████╗ ██████╗  │
│  ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔══██╗ │
│  ██████╔╝█████╗  ███████║██║  ██║██║   ██║███████║██████╔╝ │
│  ██╔══██╗██╔══╝  ██╔══██║██║  ██║██║   ██║██╔══██║██╔══██╗ │
│  ██║  ██║███████╗██║  ██║██████╔╝╚██████╔╝██║  ██║██║  ██║ │
│  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ │
└────────────────────────────────────────────────────────────┘

✓ 特点：深色背景、绿色强调、护眼
✓ 优势：长时间阅读不易疲劳
✓ 劣势：不适合打印
✓ 推荐：论文精读、夜间工作
```

### 纯净纸张 (clean_paper)

```
┌────────────────────────────────────────────────────────────┐
│ ███████╗████████╗ █████╗ ████████╗██╗ ██████╗ ███╗   ██╗  │
│ ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██║██╔═══██╗████╗  ██║  │
│ ███████╗   ██║   ███████║   ██║   ██║██║   ██║██╔██╗ ██║  │
│ ╚════██║   ██║   ██╔══██║   ██║   ██║██║   ██║██║╚██╗██║  │
│ ███████║   ██║   ██║  ██║   ██║   ██║╚██████╔╝██║ ╚████║  │
│ ╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝  │
└────────────────────────────────────────────────────────────┘

✓ 特点：白色背景、蓝色强调、学术风格
✓ 优势：适合打印、分享、导出PDF
✓ 劣势：长时间阅读可能疲劳
✓ 推荐：论文分享、打印阅读
```

### 霓虹科技 (neon_tech)

```
┌────────────────────────────────────────────────────────────┐
│ ███╗   ██╗███████╗██╗   ██╗██████╗ ███████╗██████╗ ██╗     │
│ ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗██║     │
│ ██╔██╗ ██║█████╗  ██║   ██║██████╔╝█████╗  ██████╔╝██║     │
│ ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██╔══╝  ██╔══██╗╚═╝     │
│ ██║ ╚████║███████╗╚██████╔╝██║  ██║███████╗██████╔╝██╗     │
│ ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝     │
└────────────────────────────────────────────────────────────┘

✓ 特点：深紫背景、霓虹强调、科技感
✓ 优势：视觉效果突出、适合展示
✓ 劣势：不适合长时间阅读
✓ 推荐：技术分享、演示展示
```

## 切换主题

生成的 HTML 文件支持运行时主题切换，点击右上角的主题切换按钮即可切换。

```javascript
// 切换到深色实验室
document.body.className = 'dark_lab';

// 切换到纯净纸张
document.body.className = 'clean_paper';

// 切换到霓虹科技
document.body.className = 'neon_tech';
```

## 自定义主题

如需自定义主题，可以在生成后编辑 HTML 文件，添加新的 CSS 类：

```css
body.custom_theme {
    --bg-primary: #your-bg;
    --text-primary: #your-text;
    --accent-primary: #your-accent;
    /* ... 更多变量 */
}
```

然后在 HTML 中添加切换按钮：

```html
<button onclick="document.body.className='custom_theme'">自定义主题</button>
```
