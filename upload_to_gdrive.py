import paramiko
import sys
import os
import time
from collections import Counter

def main():
    hostname = "***REMOVED_HOSTNAME***"
    username = "***REMOVED_USERNAME***"
    password = "***REMOVED_PASSWORD***"
    
    source_dir = "/home/***REMOVED_USERNAME***/tiktok-live-recorder/downloads/asmr_natty"
    dest_dir = 'gdrive:"TikTok recorder/asmr_natty"'
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("==================================================")
    print("[*] TikTok Live Recorder - Google Drive Uploader [*]")
    print("==================================================")
    
    try:
        print(f"\n[1/4] Connecting to VM ({hostname})...")
        client.connect(hostname, username=username, password=password)
        print("      [+] Connected successfully!")
        
        # Stop any existing background rclone process that we might have started earlier
        client.exec_command("pkill -f 'rclone move'")
        time.sleep(1)

        print("\n[2/4] Scanning files in the directory...")
        stdin, stdout, stderr = client.exec_command(f"find {source_dir} -type f")
        files_output = stdout.read().decode('utf-8').strip()
        
        files = [f for f in files_output.split('\n') if f]
        
        if not files:
            print("      [-] No files found to process.")
            return

        extensions = Counter()
        non_mp4_count = 0
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if not ext:
                ext = "no_extension"
            extensions[ext] += 1
            if ext != '.mp4':
                non_mp4_count += 1
                
        print(f"      [+] Found a total of {len(files)} files.")
        print("      [+] File extensions summary:")
        for ext, count in extensions.items():
            print(f"          - {ext}: {count} files")
            
        print("\n[3/4] Cleaning up non-.mp4 files...")
        if non_mp4_count > 0:
            print(f"      [*] Deleting {non_mp4_count} files that are not .mp4...")
            client.exec_command(f'find {source_dir} -type f ! -name "*.mp4" -delete')
            time.sleep(1)
            print("      [+] Non-.mp4 files deleted successfully.")
        else:
            print("      [+] No other file types found. Directory is clean.")
            
        print("\n[4/4] Starting upload of .mp4 files to Google Drive...")
        print("      (You will see live progress below. Do NOT close this window until finished)\n")
        print("-" * 50)
        
        # Run rclone with -P (Progress) and get a PTY so it outputs terminal progress correctly
        rclone_cmd = f"rclone move {source_dir} {dest_dir} --include \"*.mp4\" --drive-chunk-size 64M --transfers 4 --checkers 8 -P"
        stdin, stdout, stderr = client.exec_command(rclone_cmd, get_pty=True)
        
        # Stream the output live to the console
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(1024).decode('utf-8', errors='replace')
                sys.stdout.write(output)
                sys.stdout.flush()
            time.sleep(0.1)
            
        # Flush any remaining output
        while stdout.channel.recv_ready():
            output = stdout.channel.recv(1024).decode('utf-8', errors='replace')
            sys.stdout.write(output)
            sys.stdout.flush()
            
        exit_status = stdout.channel.recv_exit_status()
        print("\n" + "-" * 50)
        
        if exit_status == 0:
            print("\n[*] DONE! All files have been successfully uploaded and removed from the VM.")
        else:
            print(f"\n[-] Upload finished with exit code {exit_status}. There might have been some errors.")

    except Exception as e:
        print(f"\n[-] An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
