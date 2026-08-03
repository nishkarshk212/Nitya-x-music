import os

def rename_project():
    # Files to process
    extensions = ('.py', '.txt', '.md', '.json')
    
    # Process start script
    if os.path.exists('start'):
        with open('start', 'r') as f:
            content = f.read()
        if 'ishu' in content:
            with open('start', 'w') as f:
                f.write(content.replace('ishu', 'ishu'))

    # Process all other files
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '__pycache__' in root or 'downloads' in root or 'cookies' in root:
            continue
        
        for file in files:
            if file.endswith(extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'ishu' in content:
                        content = content.replace('ishu', 'ishu')
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(content)
                except Exception as e:
                    print(f"Failed to process {path}: {e}")

    # Rename the directory
    if os.path.exists('ishu'):
        os.rename('ishu', 'ishu')
        print("Successfully renamed directory 'ishu' to 'ishu'")

if __name__ == '__main__':
    rename_project()
