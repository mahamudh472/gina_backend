from django import forms
from django.utils.safestring import mark_safe

class InteractivePromptWidget(forms.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        # We render a hidden textarea and an overlay contenteditable div editor
        # with badge controls next to it.
        attrs = attrs or {}
        attrs['style'] = 'display:none;'
        textarea_html = super().render(name, value, attrs, renderer)

        # Get element ID
        element_id = attrs.get('id', 'id_' + name)

        # Define badges and their descriptions/sample values
        badges = {
            "category_label": "Entspannung",
            "goal": "innere Balance",
            "avoid": "Stress",
            "duration": "10",
            "experience": "beginner",
            "body_tension": "Schultern",
            "nature_sound": "Meeresrauschen",
            "landscape": "Wald",
            "voice_name": "Aura",
            "user_name": "Anna",
            "questionnaire_lines": "- Befinden: Gestresst\\n- Ziel: Einschlafen",
            "focus": "Stressabbau und Regulation des Nervensystems",
            "visualization": "Strand, Regen oder warme Stille",
            "affirmation": "Ich darf loslassen. Ich bin sicher.",
            "total_duration": "600"
        }

        # Build buttons HTML
        buttons_html = ""
        for key, sample in badges.items():
            buttons_html += f"""
            <button type="button" class="django-prompt-badge-btn" data-badge="{key}" title='Sample: "{sample}"'>
                + {key}
            </button>
            """

        html = f"""
        <div class="django-prompt-editor-container">
            <!-- CSS styling -->
            <style>
                .django-prompt-editor-container {{
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    background: #ffffff;
                    margin-top: 5px;
                    margin-bottom: 15px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    max-width: 100%;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-editor-container {{
                        border-color: #374151;
                        background: #1f2937;
                    }}
                }}
                .django-prompt-editor-toolbar {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    padding: 12px;
                    background: #f9fafb;
                    border-bottom: 1px solid #e5e7eb;
                    border-top-left-radius: 7px;
                    border-top-right-radius: 7px;
                    align-items: center;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-editor-toolbar {{
                        background: #111827;
                        border-bottom-color: #374151;
                    }}
                }}
                .django-prompt-editor-toolbar-title {{
                    width: 100%;
                    font-size: 0.75rem;
                    font-weight: 700;
                    color: #6b7280;
                    margin-bottom: 6px;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-editor-toolbar-title {{
                        color: #9ca3af;
                    }}
                }}
                .django-prompt-badge-btn {{
                    font-family: inherit;
                    background: #e0f2fe;
                    color: #0369a1;
                    font-size: 0.75rem;
                    font-weight: 600;
                    padding: 4px 10px;
                    border-radius: 9999px;
                    border: 1px solid #bae6fd;
                    cursor: pointer;
                    transition: all 140ms ease;
                    display: inline-flex;
                    align-items: center;
                    position: relative;
                }}
                .django-prompt-badge-btn:hover {{
                    background: #bae6fd;
                    color: #025082;
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                
                /* Colors per badge types */
                .django-prompt-badge-btn[data-badge="category_label"],
                .django-prompt-badge-btn[data-badge="focus"],
                .django-prompt-badge-btn[data-badge="visualization"],
                .django-prompt-badge-btn[data-badge="affirmation"] {{
                    background: #fef3c7;
                    color: #b45309;
                    border-color: #fde68a;
                }}
                .django-prompt-badge-btn[data-badge="category_label"]:hover,
                .django-prompt-badge-btn[data-badge="focus"]:hover,
                .django-prompt-badge-btn[data-badge="visualization"]:hover,
                .django-prompt-badge-btn[data-badge="affirmation"]:hover {{
                    background: #fde68a;
                }}
                
                .django-prompt-badge-btn[data-badge="user_name"],
                .django-prompt-badge-btn[data-badge="experience"],
                .django-prompt-badge-btn[data-badge="body_tension"] {{
                    background: #dcfce7;
                    color: #15803d;
                    border-color: #bbf7d0;
                }}
                .django-prompt-badge-btn[data-badge="user_name"]:hover,
                .django-prompt-badge-btn[data-badge="experience"]:hover,
                .django-prompt-badge-btn[data-badge="body_tension"]:hover {{
                    background: #bbf7d0;
                }}

                .django-prompt-badge-btn[data-badge="duration"],
                .django-prompt-badge-btn[data-badge="total_duration"] {{
                    background: #f3e8ff;
                    color: #6b21a8;
                    border-color: #e9d5ff;
                }}
                .django-prompt-badge-btn[data-badge="duration"]:hover,
                .django-prompt-badge-btn[data-badge="total_duration"]:hover {{
                    background: #e9d5ff;
                }}

                .django-prompt-badge-btn[data-badge="questionnaire_lines"] {{
                    background: #fee2e2;
                    color: #b91c1c;
                    border-color: #fecaca;
                }}
                .django-prompt-badge-btn[data-badge="questionnaire_lines"]:hover {{
                    background: #fecaca;
                }}

                .django-prompt-editor-content {{
                    min-height: 400px;
                    max-height: 600px;
                    overflow-y: auto;
                    padding: 16px;
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                    font-size: 0.85rem;
                    line-height: 1.6;
                    outline: none;
                    background: #ffffff;
                    color: #1f2937;
                    white-space: pre-wrap;
                    word-break: break-word;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-editor-content {{
                        background: #111827;
                        color: #e5e7eb;
                    }}
                }}
                .django-prompt-editor-content:focus {{
                    box-shadow: inset 0 0 0 2px rgba(59, 130, 246, 0.2);
                }}

                /* Rendered inline badge tags inside the editable content */
                .django-prompt-badge {{
                    background: #e0f2fe;
                    color: #0369a1;
                    border: 1px solid #bae6fd;
                    font-family: ui-sans-serif, system-ui, sans-serif;
                    font-size: 0.7rem;
                    font-weight: 700;
                    padding: 2px 6px;
                    border-radius: 4px;
                    display: inline-flex;
                    align-items: center;
                    margin: 0 3px;
                    vertical-align: middle;
                    user-select: none;
                    cursor: default;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                }}
                .django-prompt-badge .badge-sample {{
                    font-weight: 400;
                    color: #0284c7;
                    margin-left: 4px;
                    opacity: 0.85;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-badge {{
                        background: #082f49;
                        color: #38bdf8;
                        border-color: #0c4a6e;
                    }}
                    .django-prompt-badge .badge-sample {{
                        color: #7dd3fc;
                    }}
                }}

                .django-prompt-badge[data-badge="category_label"],
                .django-prompt-badge[data-badge="focus"],
                .django-prompt-badge[data-badge="visualization"],
                .django-prompt-badge[data-badge="affirmation"] {{
                    background: #fef3c7;
                    color: #b45309;
                    border-color: #fde68a;
                }}
                .django-prompt-badge[data-badge="category_label"] .badge-sample,
                .django-prompt-badge[data-badge="focus"] .badge-sample,
                .django-prompt-badge[data-badge="visualization"] .badge-sample,
                .django-prompt-badge[data-badge="affirmation"] .badge-sample {{
                    color: #d97706;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-badge[data-badge="category_label"],
                    .django-prompt-badge[data-badge="focus"],
                    .django-prompt-badge[data-badge="visualization"],
                    .django-prompt-badge[data-badge="affirmation"] {{
                        background: #451a03;
                        color: #fbbf24;
                        border-color: #78350f;
                    }}
                    .django-prompt-badge[data-badge="category_label"] .badge-sample,
                    .django-prompt-badge[data-badge="focus"] .badge-sample,
                    .django-prompt-badge[data-badge="visualization"] .badge-sample,
                    .django-prompt-badge[data-badge="affirmation"] .badge-sample {{
                        color: #f59e0b;
                    }}
                }}

                .django-prompt-badge[data-badge="user_name"],
                .django-prompt-badge[data-badge="experience"],
                .django-prompt-badge[data-badge="body_tension"] {{
                    background: #dcfce7;
                    color: #15803d;
                    border-color: #bbf7d0;
                }}
                .django-prompt-badge[data-badge="user_name"] .badge-sample,
                .django-prompt-badge[data-badge="experience"] .badge-sample,
                .django-prompt-badge[data-badge="body_tension"] .badge-sample {{
                    color: #16a34a;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-badge[data-badge="user_name"],
                    .django-prompt-badge[data-badge="experience"],
                    .django-prompt-badge[data-badge="body_tension"] {{
                        background: #064e3b;
                        color: #34d399;
                        border-color: #047857;
                    }}
                    .django-prompt-badge[data-badge="user_name"] .badge-sample,
                    .django-prompt-badge[data-badge="experience"] .badge-sample,
                    .django-prompt-badge[data-badge="body_tension"] .badge-sample {{
                        color: #10b981;
                    }}
                }}

                .django-prompt-badge[data-badge="duration"],
                .django-prompt-badge[data-badge="total_duration"] {{
                    background: #f3e8ff;
                    color: #6b21a8;
                    border-color: #e9d5ff;
                }}
                .django-prompt-badge[data-badge="duration"] .badge-sample,
                .django-prompt-badge[data-badge="total_duration"] .badge-sample {{
                    color: #9333ea;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-badge[data-badge="duration"],
                    .django-prompt-badge[data-badge="total_duration"] {{
                        background: #3b0764;
                        color: #c084fc;
                        border-color: #581c87;
                    }}
                    .django-prompt-badge[data-badge="duration"] .badge-sample,
                    .django-prompt-badge[data-badge="total_duration"] .badge-sample {{
                        color: #a855f7;
                    }}
                }}

                .django-prompt-badge[data-badge="questionnaire_lines"] {{
                    background: #fee2e2;
                    color: #b91c1c;
                    border-color: #fecaca;
                }}
                .django-prompt-badge[data-badge="questionnaire_lines"] .badge-sample {{
                    color: #dc2626;
                }}
                @media (prefers-color-scheme: dark) {{
                    .django-prompt-badge[data-badge="questionnaire_lines"] {{
                        background: #450a0a;
                        color: #f87171;
                        border-color: #7f1d1d;
                    }}
                    .django-prompt-badge[data-badge="questionnaire_lines"] .badge-sample {{
                        color: #ef4444;
                    }}
                }}
            </style>

            <!-- Toolbar with buttons -->
            <div class="django-prompt-editor-toolbar">
                <div class="django-prompt-editor-toolbar-title">Verfügbare Dynamic-Badges (Klicken zum Einfügen):</div>
                {buttons_html}
            </div>

            <!-- Standard hidden Textarea -->
            {textarea_html}

            <!-- Custom Editor Contenteditable Div -->
            <div class="django-prompt-editor-content" contenteditable="true" id="{element_id}_editor"></div>
        </div>

        <script>
        (function() {{
            const initWidget = function() {{
                const textarea = document.getElementById("{element_id}");
                const editor = document.getElementById("{element_id}_editor");
                if (!textarea || !editor || editor.dataset.initialized) return;
                
                editor.dataset.initialized = "true";
                const container = editor.closest(".django-prompt-editor-container");
                
                const badges = {{
                    "category_label": "Entspannung",
                    "goal": "innere Balance",
                    "avoid": "Stress",
                    "duration": "10",
                    "experience": "beginner",
                    "body_tension": "Schultern",
                    "nature_sound": "Meeresrauschen",
                    "landscape": "Wald",
                    "voice_name": "Aura",
                    "user_name": "Anna",
                    "questionnaire_lines": "- Befinden: Gestresst\\n- Ziel: Einschlafen",
                    "focus": "Stressabbau und Regulation des Nervensystems",
                    "visualization": "Strand, Regen oder warme Stille",
                    "affirmation": "Ich darf loslassen. Ich bin sicher.",
                    "total_duration": "600"
                }};
                
                function escapeHtml(str) {{
                    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                }}
                
                function createBadgeHTML(badgeName) {{
                    const sample = badges[badgeName] || "";
                    const cleanSample = escapeHtml(sample).replace(/"/g, '&quot;');
                    return `<span class="django-prompt-badge" data-badge="${{badgeName}}" contenteditable="false">${{badgeName}} <span class="badge-sample">("${{cleanSample}}")</span></span>`;
                }}
                
                function textToHtml(text) {{
                    let html = escapeHtml(text || "");
                    
                    // Replace placeholders with badge HTML
                    for (const key of Object.keys(badges)) {{
                        const placeholder = `\\\\{{${{key}}}}\\\\}}`;
                        const regex = new RegExp(placeholder, "g");
                        html = html.replace(regex, createBadgeHTML(key));
                    }}
                    
                    // Replace newlines with <br> for HTML rendering
                    html = html.replace(/\\r?\\n/g, "<br>");
                    return html;
                }}
                
                function htmlToText(html) {{
                    const tempDiv = document.createElement("div");
                    tempDiv.innerHTML = html;
                    
                    // Find all badges and replace them with raw placeholder text
                    const badgeElements = tempDiv.querySelectorAll(".django-prompt-badge");
                    badgeElements.forEach(badge => {{
                        const badgeName = badge.getAttribute("data-badge");
                        badge.replaceWith(`{{${{badgeName}}}}`);
                    }});
                    
                    // Convert blocks and line breaks to newlines
                    let text = "";
                    function walk(node) {{
                        if (node.nodeType === Node.TEXT_NODE) {{
                            text += node.nodeValue;
                        }} else if (node.nodeType === Node.ELEMENT_NODE) {{
                            const tagName = node.tagName.toLowerCase();
                            if (tagName === "br") {{
                                text += "\\n";
                            }} else if (tagName === "div" || tagName === "p") {{
                                if (text.length > 0 && !text.endsWith("\\n")) {{
                                    text += "\\n";
                                }}
                                for (const child of node.childNodes) {{
                                    walk(child);
                                }}
                                if (!text.endsWith("\\n")) {{
                                    text += "\\n";
                                }}
                            }} else {{
                                for (const child of node.childNodes) {{
                                    walk(child);
                                }}
                            }}
                        }}
                    }}
                    
                    for (const child of tempDiv.childNodes) {{
                        walk(child);
                    }}
                    
                    // HTML entity decode
                    const decoder = document.createElement("textarea");
                    decoder.innerHTML = text;
                    return decoder.value;
                }}
                
                // Load content
                editor.innerHTML = textToHtml(textarea.value);
                
                // Sync value to hidden textarea
                function syncValue() {{
                    textarea.value = htmlToText(editor.innerHTML);
                }}
                
                editor.addEventListener("input", syncValue);
                editor.addEventListener("blur", syncValue);
                
                // Badge button click handlers
                container.querySelectorAll(".django-prompt-badge-btn").forEach(btn => {{
                    btn.addEventListener("click", function(e) {{
                        e.preventDefault();
                        const badgeName = this.getAttribute("data-badge");
                        const badgeHtml = createBadgeHTML(badgeName) + "&nbsp;";
                        
                        editor.focus();
                        
                        // Insert at cursor
                        const selection = window.getSelection();
                        if (selection.getRangeAt && selection.rangeCount) {{
                            const range = selection.getRangeAt(0);
                            range.deleteContents();
                            
                            const el = document.createElement("div");
                            el.innerHTML = badgeHtml;
                            
                            const fragment = document.createDocumentFragment();
                            let node, lastNode;
                            while ((node = el.firstChild)) {{
                                lastNode = fragment.appendChild(node);
                            }}
                            
                            range.insertNode(fragment);
                            
                            if (lastNode) {{
                                range.setStartAfter(lastNode);
                                range.collapse(true);
                                selection.removeAllRanges();
                                selection.addRange(range);
                            }}
                        }} else {{
                            editor.innerHTML += badgeHtml;
                        }}
                        
                        syncValue();
                    }});
                }});
                
                // Auto convert typed placeholder to badge when close brace '}}' is typed
                editor.addEventListener("keyup", function(e) {{
                    if (e.key === "}}") {{
                        const selection = window.getSelection();
                        if (selection.rangeCount > 0) {{
                            const range = selection.getRangeAt(0);
                            const textNode = range.startContainer;
                            if (textNode.nodeType === Node.TEXT_NODE) {{
                                const textContent = textNode.nodeValue;
                                const cursorOffset = range.startOffset;
                                
                                const lastOpenBrace = textContent.lastIndexOf("{{", cursorOffset - 1);
                                if (lastOpenBrace !== -1) {{
                                    const possibleKey = textContent.substring(lastOpenBrace + 1, cursorOffset - 1);
                                    if (badges.hasOwnProperty(possibleKey)) {{
                                        range.setStart(textNode, lastOpenBrace);
                                        range.setEnd(textNode, cursorOffset);
                                        range.deleteContents();
                                        
                                        const tempEl = document.createElement("div");
                                        tempEl.innerHTML = createBadgeHTML(possibleKey) + "&nbsp;";
                                        
                                        const fragment = document.createDocumentFragment();
                                        let node, lastNode;
                                        while ((node = tempEl.firstChild)) {{
                                            lastNode = fragment.appendChild(node);
                                        }}
                                        range.insertNode(fragment);
                                        
                                        if (lastNode) {{
                                            range.setStartAfter(lastNode);
                                            range.collapse(true);
                                            selection.removeAllRanges();
                                            selection.addRange(range);
                                        }}
                                        syncValue();
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Intercept form submit to capture final state
                const form = textarea.closest("form");
                if (form) {{
                    form.addEventListener("submit", syncValue);
                }}
            }};
            
            // Execute on load or delayed load
            if (document.readyState === "loading") {{
                document.addEventListener("DOMContentLoaded", initWidget);
            }} else {{
                initWidget();
            }}
            // Unfold/Grappelli/django admin dynamic inline rows support
            if (window.django && window.django.jQuery) {{
                window.django.jQuery(document).on("formset:added", function() {{
                    setTimeout(initWidget, 50);
                }});
            }}
        }})();
        </script>
        """
        return mark_safe(html)
