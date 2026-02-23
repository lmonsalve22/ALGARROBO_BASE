import os
import re

vistas_dir = r"d:\GitHub\ALGARROBO_BASE\frontend\division\seguridad\admin_general\vistas2"

template = """
<div class="alert alert--info" style="margin-top: 1.5rem;">
    <strong>🤖 Análisis de Situación:</strong> <span id="{id}_ia_analysis">Analizando el comportamiento delictual de la semana...</span>
</div>
"""

for filename in os.listdir(vistas_dir):
    if filename.endswith(".html") and filename.startswith("vista"):
        filepath = os.path.join(vistas_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Determine vista ID
            match = re.search(r"vista(\d+)", filename)
            if not match: continue
            vid = match.group(1)
            span_id = f"v{vid}"
            
            # Remove existing IA block (aggressively to clean up old ones)
            content = re.sub(r'\s*<div class="alert alert--info"[\s\S]*?id="v\d+_ia_analysis"[\s\S]*?</div>', '', content)
            
            # Prepare new block
            new_block = template.format(id=span_id)
            
            # Insert after question-section
            # We assume question-section </div> closes the header block.
            # Regex: Find class="question-section", then find the next </div>
            # Since regex is greedy/lazy, we ensure we match until the first </div> after the opening tag.
            # But question-section has attributes.
            
            pattern = r'(<div class="question-section"[^>]*>[\s\S]*?</div>)'
            
            if re.search(pattern, content):
                new_content = re.sub(pattern, r'\1' + new_block, content, count=1)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")
            else:
                print(f"Skipped {filename} (Pattern not found)")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
