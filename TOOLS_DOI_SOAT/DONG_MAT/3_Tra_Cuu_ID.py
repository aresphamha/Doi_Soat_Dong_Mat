import asyncio
from telethon import TelegramClient

api_id = '28938971'
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'

async def main():
    print("=========================================")
    print("TOOL TRA CỨU CHAT ID GROUP THỦ CÔNG")
    print("=========================================")
    
    keyword = input("\nNhập tên siêu thị hoặc mã ST cần tìm (Ví dụ: A225): ").strip().lower()
    
    client = TelegramClient('user_session', api_id, api_hash)
    await client.start()
    
    print("\nĐang tìm kiếm trong danh bạ Telegram của bạn...\n")
    
    found = False
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            if keyword in dialog.title.lower():
                print(f"👉 Tên Group: {dialog.title}")
                print(f"👉 CHAT ID  : {dialog.id}")
                print("-" * 40)
                found = True
                
    if not found:
        print(f"Không tìm thấy group nào có chứa chữ '{keyword}'.")
        
    await client.disconnect()
    print("\n=========================================")
    input("Bấm Enter để thoát...")

if __name__ == '__main__':
    asyncio.run(main())
