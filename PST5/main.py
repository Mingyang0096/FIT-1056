from app.admin_utils import init_logger, backup_data
from gui.main_dashboard import launch

if __name__ == "__main__":
    
    init_logger("msms.log")

    backup_data("data/msms.json.enc", "data/backups")

    launch()

