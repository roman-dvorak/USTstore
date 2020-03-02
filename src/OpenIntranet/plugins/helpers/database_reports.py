from datetime import datetime

ACCOUNTANT_REPORT = "accountant_report"
HOURS_WORKED_REPORT = "hours_worked_report"


def save_report_file_id(database, month_date: datetime, file_id, report_type):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    database.users_reports.insert_one({
        "month": month_date,
        "type": report_type,
        "file": file_id,
        "up_to_date": True,
    })


def get_report_mdoc(database, month_date, report_type):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return database.users_reports.find_one({"month": month_date, "type": report_type})


def get_report_file_id(database, month_date, report_type):
    report_mdoc = get_report_mdoc(database, month_date, report_type)

    if not report_mdoc:
        return None

    return report_mdoc.get("file", None)


def set_report_out_of_date(database, month_date, report_type):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    database.users_reports.update_one({"month": month_date, "type": report_type},
                                      {
                                          "$set": {"up_to_date": False}
                                      })


def is_report_up_to_date(database, month_date, report_type):
    report_mdoc = get_report_mdoc(database, month_date, report_type)

    if not report_mdoc:
        return None

    return report_mdoc.get("up_to_date", None)


def set_report_up_to_date(database, month_date, report_type):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    database.users_reports.update_one({"month": month_date, "type": report_type},
                                      {
                                          "$set": {"up_to_date": True}
                                      })
