#!/bin/bash
# =============================================================================
# 单独运行解析层
# 
# 用法:
#   ./scripts/parse.sh <input.pdf> [output_dir]
#   ./scripts/parse.sh paper.pdf
#   ./scripts/parse.sh paper.pdf ./output
#   ./scripts/parse.sh https://arxiv.org/abs/1706.03762
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 解析参数
INPUT="$1"
OUTPUT_DIR="${2:-}"

if [ -z "$INPUT" ]; then
    echo -e "${RED}错误: 请提供输入文件或arXiv链接${NC}"
    echo ""
    echo "用法:"
    echo "  $0 <input.pdf> [output_dir]"
    echo "  $0 https://arxiv.org/abs/1706.03762"
    exit 1
fi

# 检查环境变量
if [ -z "$DOC2X_APIKEY" ]; then
    echo -e "${YELLOW}警告: DOC2X_APIKEY 未设置${NC}"
    echo "  请设置环境变量或使用命令行参数传入"
    echo "  export DOC2X_APIKEY='your-api-key'"
fi

# 进入项目目录
cd "$PROJECT_DIR"

# 构建命令
CMD="python -c \"
import sys
sys.path.insert(0, '.')
from parsers import Doc2XParser, ArxivHandler

input_path = '$INPUT'
output_dir = '$OUTPUT_DIR' or None

# 检测输入类型
if 'arxiv.org' in input_path or input_path.match(r'^\\d+\\.\\d+$'):
    print('检测到 arXiv 链接，正在下载...')
    handler = ArxivHandler()
    pdf_path, arxiv_id, metadata = handler.download_and_prepare(input_path)
    print(f'arXiv 下载完成: {arxiv_id}')
    input_path = pdf_path
else:
    import re
    if re.match(r'^\\d+\\.\\d+$', input_path):
        url = f'https://arxiv.org/abs/{input_path}'
        print(f'检测到 arXiv ID，正在下载...')
        handler = ArxivHandler()
        pdf_path, arxiv_id, metadata = handler.download_and_prepare(url)
        print(f'arXiv 下载完成: {arxiv_id}')
        input_path = pdf_path

# 解析 PDF
parser = Doc2XParser()
result = parser.parse(input_path, output_dir)

if result.success:
    print(f'\\n${GREEN}✓ 解析成功${NC}')
    print(f'  输出目录: {result.raw_output_dir}')
    print(f'  Markdown 长度: {len(result.markdown)} 字符')
    print(f'  图片数量: {len(result.images)}')
    
    # 写入解析结果
    import json
    output_file = f'{result.raw_output_dir}/parse_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'success': True,
            'markdown_length': len(result.markdown),
            'image_count': len(result.images),
            'metadata': result.metadata,
            'raw_output_dir': result.raw_output_dir,
            'source_file': result.source_file
        }, f, ensure_ascii=False, indent=2)
    print(f'  结果文件: {output_file}')
else:
    print(f'\\n${RED}✗ 解析失败${NC}')
    print(f'  错误: {result.error_message}')
    sys.exit(1)
\""

# 执行
eval "$CMD"
