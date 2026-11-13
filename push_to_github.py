"""
一鍵推送至 GitHub 輔助腳本 (使用純 Python Dulwich，無需安裝 Git 軟體)
使用方式：
python push_to_github.py <github_username> <repo_name> <personal_access_token>
或直接執行此腳本依提示輸入。
"""
import sys
import getpass
from dulwich import porcelain

REPO_DIR = r'C:\Users\xinfe\.gemini\antigravity\scratch\coupon_platform'

def main():
    print("=================================================================")
    print(" 🚀 DealHub 專案推送到 GitHub 工具")
    print("=================================================================")
    
    if len(sys.argv) >= 4:
        user = sys.argv[1].strip()
        repo_name = sys.argv[2].strip()
        token = sys.argv[3].strip()
    else:
        user = input("請輸入您的 GitHub 使用者名稱 (Username): ").strip()
        repo_name = input("請輸入 GitHub 儲存庫名稱 (Repo Name, 例: dealhub-coupon): ").strip()
        token = getpass.getpass("請輸入 GitHub Personal Access Token (PAT): ").strip()

    if not user or not repo_name or not token:
        print("❌ 資訊填寫不完整，操作取消。")
        return

    remote_url = f"https://{user}:{token}@github.com/{user}/{repo_name}.git"
    print(f"📡 正在連線並推送到 https://github.com/{user}/{repo_name}.git ...")
    
    try:
        repo = porcelain.open_repo(REPO_DIR)
        porcelain.push(repo, remote_url, refspecs=b'refs/heads/master:refs/heads/main')
        print("🎉 程式碼已成功推送至 GitHub！現在可以在 Render.com 點擊部署囉！")
    except Exception as e:
        print(f"❌ 推送失敗: {e}")
        print("提示：若儲存庫預設分支為 master，可檢查 Token 權限是否包含 repo 存取權。")

if __name__ == '__main__':
    main()
