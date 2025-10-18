from app.admin_utils import init_logger, backup_data
from gui.main_dashboard import launch

if __name__ == "__main__":
    # 1) 启动前初始化日志（Fragment 5.4 要求）
    init_logger("msms.log")

    # 2) 启动前做一次数据备份（Fragment 5.4 要求）
    #    如果你当前以加密方式运行，数据文件通常为 data/msms.json.enc；
    #    若是明文运行，请改成 data/msms.json。
    backup_data("data/msms.json.enc", "data/backups")

    # 3) 启动 GUI
    launch()

