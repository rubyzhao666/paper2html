#!/bin/bash
# =============================================================================
# 完整管线：PDF/arXiv → HTML
# 
# 用法:
#   ./scripts/generate.sh <input> <output.html> [style]
#   ./scripts/generate.sh paper.pdf output.html
#   ./scripts/generate.sh paper.pdf output.html dark_lab
#   ./scripts/generate.sh https://arxiv.org/abs/1706.03762 output.html
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 解析参数
INPUT="$1"
OUTPUT="$2"
STYLE="${3:-dark_lab}"

# 参数检查
if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo -e "${RED}错误: 缺少必需参数${NC}"
    echo ""
    echo "用法:"
    echo "  $0 <input> <output.html> [style]"
    echo ""
    echo "参数:"
    echo "  input     输入文件（PDF路径或arXiv链接）"
    echo "  output    输出HTML文件路径"
    echo "  style     样式预设 (dark_lab|clean_paper|neon_tech)，默认: dark_lab"
    echo ""
    echo "示例:"
    echo "  $0 paper.pdf output.html"
    echo "  $0 https://arxiv.org/abs/1706.03762 output.html"
    echo "  $0 paper.pdf output.html neon_tech"
    exit 1
fi

# 验证样式参数
if [[ ! "$STYLE" =~ ^(dark_lab|clean_paper|neon_tech)$ ]]; then
    echo -e "${RED}错误: 不支持的样式 '$STYLE'${NC}"
    echo "支持的样式: dark_lab, clean_paper, neon_tech"
    exit 1
fi

# 打印配置
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  paper2html 完整管线${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  ${YELLOW}输入:${NC}   $INPUT"
echo -e "  ${YELLOW}输出:${NC}   $OUTPUT"
echo -e "  ${YELLOW}样式:${NC}   $STYLE"
echo ""

# 检查 API Key
if [ -z "$DOC2X_APIKEY" ]; then
    echo -e "${YELLOW}⚠  DOC2X_APIKEY 未设置${NC}"
fi

if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}⚠  DEEPSEEK_API_KEY 未设置（理解层将被跳过）${NC}"
    echo "   如需完整功能，请设置: export DEEPSEEK_API_KEY='your-key'"
fi

echo ""

# 进入项目目录
cd "$PROJECT_DIR"

# 执行转换
echo -e "${BLUE}🚀 开始转换...${NC}"
echo ""

python paper2html.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --style "$STYLE"

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ 转换完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  📄 输出文件: ${GREEN}$OUTPUT${NC}"
    echo ""
    
    # 显示文件大小
    if [ -f "$OUTPUT" ]; then
        SIZE=$(du -h "$OUTPUT" | cut -f1)
        echo -e "  📦 文件大小: $SIZE"
    fi
    
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ❌ 转换失败${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "请检查:"
    echo "  1. API Key 是否正确"
    echo "  2. 网络连接是否正常"
    echo "  3. 输入文件是否存在"
    echo ""
    echo "使用 --debug 查看详细日志"
    exit 1
fi
