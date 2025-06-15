#!/usr/bin/env python3
"""
啟動 Game Engine Server 的腳本
"""
import asyncio
import sys
import os
import argparse
import subprocess
import signal
import time

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'catanatron'))

from catanatron.multiplayer.game_engine_server import GameEngineServer

def check_port_usage(ports):
    """檢查指定端口是否被占用，返回占用的進程信息"""
    occupied_ports = {}
    
    for port in ports:
        try:
            # 使用 lsof 檢查端口占用
            result = subprocess.run(
                ['lsof', '-i', f':{port}'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # 第一行是標題
                    # 解析進程信息
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 2:
                            command = parts[0]
                            pid = parts[1]
                            occupied_ports[port] = {'command': command, 'pid': pid}
                            break
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # 如果 lsof 不可用或超時，跳過
            continue
    
    return occupied_ports

def kill_processes_by_pids(pids):
    """終止指定 PID 的進程"""
    killed_pids = []
    
    for pid in pids:
        try:
            pid_int = int(pid)
            print(f"   🔪 終止進程 PID {pid_int}...")
            
            # 嘗試優雅終止
            os.kill(pid_int, signal.SIGTERM)
            time.sleep(1)
            
            # 檢查進程是否還存在
            try:
                os.kill(pid_int, 0)  # 檢查進程是否存在
                print(f"   💀 強制終止進程 PID {pid_int}...")
                os.kill(pid_int, signal.SIGKILL)
            except OSError:
                pass  # 進程已經不存在了
                
            killed_pids.append(pid)
            
        except (ValueError, OSError) as e:
            print(f"   ❌ 無法終止進程 PID {pid}: {e}")
    
    return killed_pids

def cleanup_ports(ports):
    """清理占用指定端口的進程"""
    print("🧹 檢查端口占用情況...")
    
    occupied = check_port_usage(ports)
    
    if not occupied:
        print("   ✅ 所有端口都可用")
        return True
    
    print(f"   ⚠️  發現 {len(occupied)} 個端口被占用:")
    pids_to_kill = set()
    
    for port, info in occupied.items():
        print(f"     端口 {port}: {info['command']} (PID {info['pid']})")
        pids_to_kill.add(info['pid'])
    
    print("   🔧 開始清理進程...")
    killed_pids = kill_processes_by_pids(pids_to_kill)
    
    if killed_pids:
        print(f"   ✅ 已終止 {len(killed_pids)} 個進程")
        time.sleep(2)  # 等待進程完全終止
        
        # 再次檢查端口
        remaining = check_port_usage(ports)
        if remaining:
            print(f"   ⚠️  仍有 {len(remaining)} 個端口被占用")
            return False
        else:
            print("   🎉 所有端口已清理完成")
            return True
    else:
        print("   ❌ 未能清理任何進程")
        return False

async def main():
    parser = argparse.ArgumentParser(description='啟動 Catanatron 遊戲伺服器')
    parser.add_argument('--min-players', type=int, default=2, 
                       help='最少玩家數量 (預設: 2)')
    parser.add_argument('--max-players', type=int, default=4, 
                       help='最多玩家數量 (預設: 4)')
    parser.add_argument('--wait-time', type=int, default=30,
                       help='達到最少玩家數後等待時間(秒) (預設: 30)')
    parser.add_argument('--host', type=str, default="0.0.0.0",
                       help='伺服器主機地址 (預設: 0.0.0.0)')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='跳過端口清理步驟')
    
    args = parser.parse_args()
    
    # 驗證參數
    if args.min_players < 2:
        print("❌ 錯誤：最少玩家數量必須至少為 2")
        return
    if args.max_players > 4:
        print("❌ 錯誤：最多玩家數量不能超過 4 (顏色限制)")
        return
    if args.min_players > args.max_players:
        print("❌ 錯誤：最少玩家數量不能大於最多玩家數量")
        return
    
    # 計算需要的端口
    ports_needed = [8001 + i for i in range(args.max_players)]
    
    # 自動清理端口（除非用戶指定跳過）
    if not args.no_cleanup:
        if not cleanup_ports(ports_needed):
            print("❌ 端口清理失敗，請手動處理或使用 --no-cleanup 參數跳過")
            return
    
    server = GameEngineServer(
        host=args.host,
        min_players=args.min_players, 
        max_players=args.max_players
    )
    server.waiting_time = args.wait_time
    
    print("🎮 Starting Catanatron Game Engine Server...")
    print(f"⚙️  Configuration:")
    print(f"   Minimum players: {args.min_players}")
    print(f"   Maximum players: {args.max_players}")
    print(f"   Wait time: {args.wait_time} seconds")
    print(f"   Host: {args.host}")
    print()
    print("🌐 Players can connect to:")
    
    colors = ["RED", "BLUE", "WHITE", "ORANGE"]
    for i in range(args.max_players):
        port = 8001 + i
        color = colors[i]
        print(f"   Port {port}: {color} player")
    
    print()
    print("📝 Game Rules:")
    print(f"   • Need at least {args.min_players} players to start")
    print(f"   • Support up to {args.max_players} players maximum")
    print(f"   • Game starts after {args.wait_time}s when minimum reached")
    print("   • Players can join anytime until maximum reached")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        await server.start_all_servers()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")

if __name__ == "__main__":
    asyncio.run(main())