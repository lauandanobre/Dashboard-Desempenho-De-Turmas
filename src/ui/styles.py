"""Folha de estilo (QSS): visual sóbrio e plano. Sem sombras e sem animações."""

NAVY = "#3B5B92"
NAVY_DARK = "#324E7E"

QSS = f"""
* {{ font-size: 13px; }}
QMainWindow, QWidget#page {{ background: #F4F5F7; }}
QWidget {{ color: #26303B; }}
QFrame#header {{ background: #FFFFFF; border-bottom: 1px solid #D5D9DF; }}
QLabel#appTitle {{ font-size: 17px; font-weight: 600; }}
QLabel#fileName {{ color: #5B6573; }}
QListWidget#nav {{ background: #26303B; border: none; outline: 0; }}
QListWidget#nav::item {{ color: #D9DEE5; padding: 11px 16px; }}
QListWidget#nav::item:selected {{ background: {NAVY}; color: #FFFFFF; }}
QFrame#card {{ background: #FFFFFF; border: 1px solid #D5D9DF; border-radius: 2px; }}
QLabel#kpiTitle {{ color: #5B6573; font-size: 12px; }}
QLabel#kpiValue {{ font-size: 20px; font-weight: 600; }}
QLabel#emptyTitle {{ font-size: 18px; font-weight: 600; }}
QLabel#muted {{ color: #5B6573; }}
QPushButton {{ background: #FFFFFF; border: 1px solid #B8BEC8; padding: 6px 14px; border-radius: 2px; }}
QPushButton:hover {{ background: #EEF0F3; }}
QPushButton:disabled {{ color: #9AA1AD; background: #F4F5F7; }}
QPushButton#primary {{ background: {NAVY}; border: 1px solid {NAVY}; color: #FFFFFF; }}
QPushButton#primary:hover {{ background: {NAVY_DARK}; }}
QComboBox, QDoubleSpinBox, QLineEdit {{ background: #FFFFFF; border: 1px solid #B8BEC8; padding: 4px 6px; border-radius: 2px; }}
QListWidget, QTableView, QTextBrowser {{ background: #FFFFFF; border: 1px solid #D5D9DF; }}
QHeaderView::section {{ background: #E9ECF0; border: none; border-right: 1px solid #D5D9DF;
                        border-bottom: 1px solid #D5D9DF; padding: 5px 8px; font-weight: 600; }}
QTabWidget::pane {{ border: 1px solid #D5D9DF; background: #FFFFFF; }}
QTabBar::tab {{ background: #E9ECF0; padding: 8px 16px; border: 1px solid #D5D9DF; border-bottom: none; }}
QTabBar::tab:selected {{ background: #FFFFFF; }}
QTabBar::tab:disabled {{ color: #9AA1AD; }}
QGroupBox {{ border: 1px solid #D5D9DF; margin-top: 12px; padding-top: 10px; background: #FFFFFF; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #5B6573; }}
"""
