$sha = (Get-FileHash gui\tabs\chat_tab.py -Algorithm SHA256).Hash
python tools\safe_replace.py --path gui\tabs\chat_tab.py --expected-sha $sha --new tmp\chat_tab_fixed.py

