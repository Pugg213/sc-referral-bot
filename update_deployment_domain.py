#!/usr/bin/env python3
"""
DEPLOYMENT DOMAIN UPDATER
Автоматически обновляет все конфигурации для нового deployment домена
"""
import os
import json

def update_deployment_domain(new_domain):
    """Update all configurations with new deployment domain"""
    
    print(f"🔄 Updating deployment domain to: {new_domain}")
    
    # Update TON Connect manifests
    manifest_files = [
        "dist/tonconnect-manifest.json",
        "public/tonconnect-manifest.json"
    ]
    
    for manifest_file in manifest_files:
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                manifest["url"] = f"https://{new_domain}"
                manifest["iconUrl"] = f"https://{new_domain}/icon.svg"
                
                with open(manifest_file, 'w') as f:
                    json.dump(manifest, f, indent=4)
                
                print(f"✅ Updated {manifest_file}")
                
            except Exception as e:
                print(f"❌ Error updating {manifest_file}: {e}")
    
    # Set environment variable for runtime
    os.environ["REPLIT_DEPLOYMENT_DOMAIN"] = new_domain
    print(f"✅ Set REPLIT_DEPLOYMENT_DOMAIN={new_domain}")
    
    print("🚀 All configurations updated for deployment!")

if __name__ == "__main__":
    # DISABLED: Prevents automatic webhook switching
    print("❌ Auto-domain update DISABLED to prevent webhook conflicts")
    print("   Manual deployment domain update required if needed")
    # PERMANENTLY DISABLED: This domain causes webhook switching issues
    # All domain switching functionality removed for stability