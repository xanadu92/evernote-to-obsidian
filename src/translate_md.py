import os
import sys
import argparse
from pathlib import Path
from deep_translator import GoogleTranslator

# Reconfigure stdout/stderr to use UTF-8 encoding on Windows consoles
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def translate_with_fallback(text):
    lines = text.split('\n')
    translator = GoogleTranslator(source='auto', target='ko')
    
    in_code_block = False
    in_frontmatter = False
    
    translated_lines = []
    buffer = []
    
    def flush_buffer():
        if not buffer:
            return
        chunk = '\n'.join(buffer)
        if chunk.strip():
            try:
                # deep-translator max chars is 5000, we should be careful but usually paragraphs are small
                if len(chunk) > 4900:
                    # just split by lines if too long
                    for l in buffer:
                        if l.strip():
                            res = translator.translate(l)
                            translated_lines.append(res if res else l)
                        else:
                            translated_lines.append(l)
                else:
                    res = translator.translate(chunk)
                    if res:
                        translated_lines.extend(res.split('\n'))
                    else:
                        translated_lines.extend(buffer)
            except Exception as e:
                print(f"  [!] Fallback translation error: {e}")
                translated_lines.extend(buffer)
        else:
            translated_lines.extend(buffer)
        buffer.clear()
        
    for i, line in enumerate(lines):
        # Frontmatter
        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            flush_buffer()
            translated_lines.append(line)
            continue
            
        if in_frontmatter:
            translated_lines.append(line)
            if line.strip() == '---':
                in_frontmatter = False
            continue
            
        # Code block
        if line.strip().startswith('```'):
            flush_buffer()
            in_code_block = not in_code_block
            translated_lines.append(line)
            continue
            
        if in_code_block:
            translated_lines.append(line)
            continue
            
        # Normal text: flush on empty lines or markdown elements like headings and lists to preserve structure
        if not line.strip() or line.strip().startswith('#') or line.strip().startswith('-') or line.strip().startswith('!['):
            flush_buffer()
            if line.strip():
                # translate this single line and append
                try:
                    res = translator.translate(line)
                    translated_lines.append(res if res else line)
                except:
                    translated_lines.append(line)
            else:
                translated_lines.append(line)
            continue
            
        buffer.append(line)
        
    flush_buffer()
    return '\n'.join(translated_lines)

def process_file(filepath):
    print(f"[*] Processing {filepath}...")
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"[!] Cannot read file {filepath}: {e}")
        return
        
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    translated_content = None
    
    if has_gemini:
        try:
            from google import genai
            client = genai.Client()
            prompt = "You are a professional translator. Translate the following Markdown text to Korean. Preserve all Markdown formatting, frontmatter, code blocks, and links perfectly. Output only the translated text.\n\n"
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt + content,
            )
            translated_content = response.text
            
            # Clean up potential markdown formatting wrapping added by Gemini
            if translated_content.startswith('```markdown\n') and translated_content.endswith('```') and not content.startswith('```markdown'):
                translated_content = translated_content[12:-3].strip()
                
            print("  [+] Translated using Gemini API.")
        except Exception as e:
            print(f"  [!] Gemini API failed: {e}. Falling back to Google Translate.")
            translated_content = translate_with_fallback(content)
            print("  [+] Translated using Fallback (Google Translate).")
    else:
        print("  [!] GEMINI_API_KEY not found. Using Fallback (Google Translate).")
        translated_content = translate_with_fallback(content)
        print("  [+] Translated using Fallback (Google Translate).")
        
    if translated_content:
        new_filepath = filepath.with_name(f"{filepath.stem}_ko{filepath.suffix}")
        try:
            new_filepath.write_text(translated_content, encoding='utf-8')
            print(f"  [+] Saved to {new_filepath}")
        except Exception as e:
            print(f"  [!] Failed to save {new_filepath}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Translate Markdown files to Korean.")
    parser.add_argument("path", help="Path to a markdown file or directory.")
    args = parser.parse_args()
    
    target_path = Path(args.path)
    
    if not target_path.exists():
        print(f"[!] Path not found: {target_path}")
        return
        
    if target_path.is_file():
        if target_path.suffix.lower() == '.md':
            process_file(target_path)
        else:
            print("[!] Not a markdown file.")
    elif target_path.is_dir():
        for file in target_path.rglob("*.md"):
            if not file.stem.endswith("_ko"):
                process_file(file)

if __name__ == "__main__":
    main()
