# 에버노트(Evernote) to 옵시디언(Obsidian) 마크다운 변환 도구

이 도구는 에버노트(Evernote)의 노트들을 자동으로 다운로드하여 로컬 백업을 생성하고, 이를 옵시디언(Obsidian)에서 즉시 사용할 수 있는 마크다운(Markdown) 포맷으로 변환해 줍니다.

---

## 주요 기능

1. **에버노트 클라우드 백업:**
   - `evernote-backup` 라이브러리를 제어하여 클라우드의 모든 노트북 데이터를 로컬 SQLite DB로 동기화하고 노트북 단위로 `.enex` 파일을 일괄 자동 추출합니다.
2. **옵시디언 마크다운 변환:**
   - 에버노트 노트 내용(ENML)을 표준 GitHub Flavored Markdown(GFM) 형식으로 파싱하여 변환합니다.
   - 제목 중복 발생 시 **생성 시간 타임스탬프**를 파일명 뒤에 자동으로 부착하여 충돌을 회방합니다. (예: `회의록_20260612_010712.md`)
   - 텍스트 하이라이트(span background color) 속성을 옵시디언 전용 하이라이트 문법(`==텍스트==`)으로 자동 치환합니다.
   - 체크리스트(`<en-todo>`) 항목을 본문 또는 리스트 형식에 맞춰 깔끔한 체크박스(`- [ ]` / `- [x]`)로 변환합니다.
3. **첨부파일 추출 및 상대 경로 자동 맵핑 (옵션 B 반영):**
   - 이미지, PDF 등 노트에 내장된 모든 첨부 파일을 추출하여 지정된 `attachments/` 폴더에 분류하여 저장합니다.
   - 마크다운 본문 내 첨부 파일 링크는 범용성이 높은 **표준 마크다운 상대 경로 링크** 형식으로 삽입됩니다.
     - 예시: `![첨부파일이름.png](../attachments/첨부파일이름.png)`
4. **노트 간 내부 링크 복원:**
   - 에버노트 전용 내부 링크(`evernote:///view/...`)를 분석하여 변환된 마크다운 노트 간의 **상대 경로 마크다운 링크**로 자동 재구축합니다.

---

## 설치 및 사전 준비

### 1. FFMPEG 설치
비디오/오디오 다운로드 및 인코딩에 필요한 `ffmpeg`가 시스템 PATH에 설치되어 있어야 에버노트 백업 라이브러리가 올바르게 작동할 수 있습니다.

### 2. 파이썬 의존성 패키지 설치
이 폴더(`d:/AIProject/Evernote`)에서 아래 명령을 실행하여 프로젝트를 개발 모드로 설치합니다. 필요한 패키지가 함께 자동 설치됩니다.
```bash
pip install -e .
```

---

## 사용 방법

이 도구는 `evernote-convert` 라는 CLI 명령어로 실행할 수 있으며, 또는 `python -m src.main`으로도 실행할 수 있습니다.

### 1. 전체 프로세스 한번에 실행 (`run-all`)
클라우드 동기화부터 마크다운 변환까지의 과정을 하나의 명령어로 연속 수행합니다.
```bash
evernote-convert run-all --output obsidian_vault
```
* **최초 실행 시:** OAuth 로그인을 위해 웹 브라우저 창이 자동으로 열립니다. 에버노트 계정 로그인 후 인증 권한을 승인해 주시면 동기화가 진행됩니다. 이후 실행 시에는 세션이 유지되어 즉시 실행됩니다.

### 2. 개별 단계 실행

#### 단계 A: 에버노트 동기화 및 백업 (`sync`)
클라우드의 에버노트 데이터를 다운로드하여 로컬 데이터베이스에 동기화하고 `.enex` 파일을 만듭니다.
```bash
evernote-convert sync --db evernote_backup.db --export-dir evernote_exports
```
- `--db`: 백업 DB 저장 경로 (기본값: `evernote_backup.db`)
- `--export-dir`: `.enex` 파일들이 임시 추출될 디렉토리 (기본값: `evernote_exports`)
- `--force-init`: 로그인 정보를 초기화하고 새로 OAuth 인증을 받고 싶을 때 사용

#### 단계 B: ENEX 백업 파일을 마크다운으로 변환 (`convert`)
백업된 `.enex` 파일 디렉토리를 파싱하여 옵시디언 금고(Vault) 형식으로 마크다운 파일을 일괄 생성합니다.
```bash
evernote-convert convert --input evernote_exports --output obsidian_vault --attachments attachments
```
- `--input`: `.enex` 백업 파일 디렉토리
- `--output`: 변환 결과가 저장될 옵시디언 금고 폴더명 (기본값: `obsidian_vault`)
- `--attachments`: 옵시디언 금고 하위에 생성될 첨부 파일 폴더명 (기본값: `attachments`)

---

---

## MCP (Model Context Protocol) 서버 연동

이 도구는 외부 AI 에이전트 및 개발 도구(Cursor, Claude Desktop 등)와 연동하여 자율적으로 작동할 수 있도록 **Model Context Protocol (MCP)** 규격을 지원합니다. 특정 AI 에이전트에 종속되지 않는 범용 플러그인 형태로 동작합니다.

### 1. MCP 서버 구동 방법
패키지 설치가 완료되면, CLI 명령어로 직접 구동할 수 있습니다 (기본 stdio 트랜스포트 사용):
```bash
evernote-mcp
```
또는 Python 모듈로 실행할 수도 있습니다:
```bash
python -m src.mcp_server
```

### 2. MCP 클라이언트 설정 예시 (`mcp_config.json`)
Cursor나 Claude Desktop 등 외부 클라이언트에서 사용하려면 설정 파일에 아래와 같이 서버를 등록합니다.

```json
{
  "mcpServers": {
    "evernote-to-obsidian": {
      "command": "evernote-mcp"
    }
  }
}
```
*(만약 전역 명령어 실행이 원활하지 않은 경우, python 인터프리터 절대 경로와 모듈 실행 인자를 명시적으로 설정할 수 있습니다.)*

### 3. 제공되는 MCP 도구 (Tools)
서버 구동 시 AI 에이전트에게 노출되어 호출 가능한 도구 목록입니다:

* **`sync_evernote`**: 에버노트 클라우드 데이터를 SQLite DB로 동기화하고 `.enex` 백업 파일을 로컬로 추출합니다.
  - 인자: `db_path` (기본값: `evernote_backup.db`), `export_dir` (기본값: `evernote_exports`), `force_init` (로그인 정보 초기화 여부)
* **`convert_enex`**: 추출된 `.enex` 백업 파일을 파싱하여 옵시디언 마크다운 노트로 변환합니다.
  - 인자: `input_dir` (기본값: `evernote_exports`), `output_dir` (기본값: `obsidian_vault`), `attachments_subdir` (기본값: `attachments`), `download_images` (이미지 다운로드 및 현지화 처리 여부)
* **`download_images`**: 생성된 마크다운 파일들의 외부 이미지 URL을 다운로드하여 로컬에 첨부파일 형태로 저장하고 본문 링크를 변경합니다.
  - 인자: `vault_dir` (기본값: `obsidian_vault`), `attachments_subdir` (기본값: `attachments`)
* **`run_all`**: 동기화, 변환, 이미지 다운로드(옵션) 과정을 순차적으로 한 번에 수행합니다.
  - 인자: `db_path`, `export_dir`, `output_dir`, `attachments_subdir`, `force_init`, `download_images`

---

## 프로젝트 파일 설명

* `src/main.py`: CLI 실행 스크립트. 명령어 옵션을 정의하고 동작을 분기합니다.
* `src/mcp_server.py`: Model Context Protocol (MCP) 표준 규격의 스튜디오 기반 도구 서버 엔트리포인트입니다.
* `src/backup_manager.py`: `evernote-backup` 서브프로세스를 실행하고 제어합니다.
* `src/enex_parser.py`: `.enex` 파일 내부 XML 트리 분석, 첨부 파일 추출, ENML 본문의 마크다운 변환 핵심 로직을 담당합니다.
* `src/link_resolver.py`: 노트의 생성 시간 타임스탬프를 매핑하여 중복 파일명을 조율하고, 에버노트 GUID를 통한 내부 링크 복원을 처리합니다.
