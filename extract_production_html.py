#!/usr/bin/env python3
"""Extract HTML files from production container for analysis"""

import subprocess
import os
import tempfile
from datetime import datetime

def extract_html_from_production():
    """Extract HTML files from Azure Container Apps"""
    print("🔍 Extracting HTML files from production container...")
    
    try:
        # List files in /tmp directory
        print("📂 Listing files in production /tmp directory...")
        result = subprocess.run([
            "az", "containerapp", "exec",
            "--name", "hr-pong-scraper",
            "--resource-group", "pingpong-betting-rg",
            "--command", "ls -la /tmp/debug_html_*.html || echo 'No debug HTML files found'"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("📋 Production /tmp directory contents:")
            print(result.stdout)
            
            # Try to get the HTML files
            if "debug_html_" in result.stdout:
                print("🔄 Attempting to extract HTML content...")
                
                # Get first HTML file
                lines = result.stdout.strip().split('\n')
                html_files = [line.split()[-1] for line in lines if 'debug_html_' in line and '.html' in line]
                
                if html_files:
                    html_file = html_files[0]
                    print(f"📥 Extracting content from {html_file}")
                    
                    # Get file content
                    result2 = subprocess.run([
                        "az", "containerapp", "exec",
                        "--name", "hr-pong-scraper", 
                        "--resource-group", "pingpong-betting-rg",
                        "--command", f"head -c 5000 {html_file}"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result2.returncode == 0:
                        # Save to local file
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        local_file = f"production_html_extract_{timestamp}.html"
                        
                        with open(local_file, 'w', encoding='utf-8') as f:
                            f.write(result2.stdout)
                        
                        print(f"💾 Saved first 5000 chars to {local_file}")
                        print(f"📊 Content preview (first 500 chars):")
                        print("-" * 50)
                        print(result2.stdout[:500])
                        print("-" * 50)
                        
                        # Check for key elements
                        content = result2.stdout
                        print(f"\n🔍 Content analysis:")
                        print(f"   Size: {len(content):,} characters")
                        print(f"   Contains '.hr-market-view': {'hr-market-view' in content}")
                        print(f"   Contains '.selection-odds': {'selection-odds' in content}")
                        print(f"   Contains '.selection-container': {'selection-container' in content}")
                        print(f"   Contains '.scoreContainer': {'scoreContainer' in content}")
                        print(f"   Contains 'class=\"event\"': {'class="event"' in content}")
                        
                        return local_file
                    else:
                        print(f"❌ Failed to extract HTML content: {result2.stderr}")
                else:
                    print("❌ No HTML files found in listing")
            else:
                print("❌ No debug HTML files found")
        else:
            print(f"❌ Failed to list files: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

if __name__ == "__main__":
    extract_html_from_production()