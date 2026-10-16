"""Validate local assets and create portable deliverables. Standard library only."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import date, timedelta
import base64
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for attr in ('src', 'href'):
            if attr in attrs:
                self.references.append(attrs[attr])

checks = []
for name in ('preview.html', 'wireframes.html'):
    path = ROOT / 'design' / name
    document = Document()
    document.feed(path.read_text(encoding='utf-8'))
    assert len(document.ids) == len(set(document.ids)), 'Duplicate IDs: ' + name
    for ref in document.references:
        if ref.startswith(('#', 'data:', 'http:', 'https:')):
            continue
        assert (path.parent / ref).exists(), 'Missing file: ' + ref
    if name == 'preview.html':
        script = (ROOT / 'design/preview.js').read_text(encoding='utf-8')
        for target in re.findall(r"byId\('([^']+)'\)", script):
            assert target in document.ids, 'Missing DOM target: ' + target
    checks.append(name + ': unique IDs and local references verified')

for path in (ROOT / 'ui/assets').glob('*.svg'):
    ET.parse(path)
checks.append('Four SVG assets: XML parsed')
subprocess.run(['node', '--check', str(ROOT / 'design/preview.js')], check=True)
checks.append('preview.js: node --check passed')

start, end = date(2026, 10, 20), date(2026, 11, 19)
days = [start + timedelta(days=i) for i in range((end-start).days+1)]
assert len([day for day in days if day.weekday() in (1,2,3,4)]) == 19
assert (date(2026,11,20)-start).days == 31
checks.append('Study calendar: 19 meetings, D-31 on October 20')

def data_uri(path):
    return 'data:image/svg+xml;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

# Single-file offline preview for downloading separately from the full archive.
html = (ROOT / 'design/preview.html').read_text(encoding='utf-8')
css = (ROOT / 'ui/tokens.css').read_text(encoding='utf-8') + '\n' + (ROOT / 'design/preview.css').read_text(encoding='utf-8')
html = re.sub(r'<link rel="stylesheet"[^>]+>', '', html)
html = html.replace('</head>', '<style>' + css + '</style></head>')
script = (ROOT / 'design/preview.js').read_text(encoding='utf-8')
uris = {name: data_uri(ROOT / ('ui/assets/' + name + '.svg')) for name in ('tree', 'tree-library')}
script = 'const embeddedTreeAssets=' + json.dumps(uris) + ';\n' + script
script = script.replace("`../ui/assets/${tree.library?'tree-library':'tree'}.svg`", "embeddedTreeAssets[tree.library?'tree-library':'tree']")
html = html.replace('<script src="preview.js"></script>', '<script>' + script + '</script>')
for name, uri in uris.items():
    html = html.replace('../ui/assets/' + name + '.svg', uri)
(ROOT / 'design/design-preview-standalone.html').write_text(html, encoding='utf-8')
checks.append('Standalone preview: CSS, JavaScript and SVG embedded')

report = '# 검증 기록\n\n2026-10-16 · 기획/UI 전달 패키지\n\n'
report += '\n'.join('- ' + check for check in checks)
report += '\n\n## 확인 제한\n브라우저 도구의 로컬 서버 연결이 시간 초과되었고, file URL 열기는 브라우저 정책으로 허용되지 않았습니다. 따라서 실제 브라우저의 PC·모바일 화면 렌더링과 클릭 동작은 이번 환경에서 검증하지 못했습니다. 반응형 CSS와 입력 동작 소스는 제공하지만 시각 검수 완료로 주장하지 않습니다. React JSX의 Vite 빌드와 서버 연동도 Claude Code 개발 단계에서 검증해야 합니다.\n\n## 사용자 미리보기 확인 순서\n1. design-preview-standalone.html을 브라우저에서 열기.\n2. 대시보드에서 목표 추가·체크, 타이머 상태 시연 확인.\n3. 내 숲 → 수납함 선택 → 빈 칸 클릭 → 나무 이동 → 수납하기.\n4. 기록 화면에서 보충 목표·회고 저장 안내 확인.\n5. 창 폭을 1440/1280/390/360으로 바꾸어 겹침과 가로 스크롤 확인.\n6. 모바일에서는 칸 목록과 하단 메뉴, 설정 버튼 확인.\n\n서버·인증·DB·실제 타이머·알림 권한·Git 커밋은 이 패키지에서 실행하지 않았습니다.\n'
(ROOT / 'docs/04-verification.md').write_text(report, encoding='utf-8')

archive = ROOT.parent / 'tree-for-study-planning-ui-v1.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for file in sorted(ROOT.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts:
            output.write(file, file.relative_to(ROOT.parent))
with zipfile.ZipFile(archive) as output:
    assert output.testzip() is None
print('\n'.join(checks))
print('ZIP integrity verified:', archive.name)
print('Packaged files:', len(list(ROOT.rglob('*'))))
