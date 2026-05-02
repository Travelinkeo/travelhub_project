with open('hang_dump.txt', 'rb') as f:
    content = f.read()
    # Try to decode from UTF-16LE or UTF-8
    try:
        text = content.decode('utf-16')
    except:
        text = content.decode('utf-8', errors='ignore')
    
    lines = text.splitlines()
    for line in lines[:100]:
        print(line)
