from .backend import attendance, users


def get_plugin_handlers():
    users_base_name = "users"
    attendance_base_name = "attendance"

    return [
        (r'/{}/vue/?(.*)'.format(users_base_name), users.VueStaticFileHandler, {
            "path": "plugins/users/frontend/dist",
            "default_filename": "index.html"
        }),
        # (r'/{}/api/users'.format(users_base_name), users.ApiUsersHandler),
        # (r'/{}/api/users/(.*)'.format(users_base_name), users.ApiUsersHandler),
        (r'/{}/api/users/current'.format(users_base_name), users.ApiCurrentUserHandler),
        (r'/{}/api/users/(.*)/contracts'.format(users_base_name), users.ApiContractsHandler),
        # (r'/{}/api/users/(.*)/contracts/(.*)'.format(users_base_name), users.ApiContractsHandler),
        # (r'/{}/api/users/(.*)/documents'.format(users_base_name), users.ApiDocumentsHandler),
        # (r'/{}/api/users/(.*)/documents/(.*)'.format(users_base_name), users.ApiDocumentsHandler),

        # old
        (r'/{}/api/admintable'.format(users_base_name), users.ApiAdminTableHandler),
        (r'/{}/api/u/(.*)/edit'.format(users_base_name), users.ApiEditUserHandler),
        (r'/{}/api/u/(.*)/contracts/add'.format(users_base_name), users.ApiAddContractHandler),
        (r'/{}/api/u/(.*)/contracts/invalidate'.format(users_base_name), users.ApiInvalidateContractHandler),
        (r'/{}/api/u/(.*)/contracts/scan'.format(users_base_name), users.ApiUploadContractScanHandler),
        (r'/{}/api/u/(.*)/contracts/finalize'.format(users_base_name), users.ApiFinalizeContractHandler),
        (r'/{}/api/u/(.*)/documents/add'.format(users_base_name), users.ApiAddDocumentHandler),
        (r'/{}/api/u/(.*)/documents/invalidate'.format(users_base_name), users.ApiInvalidateDocumentHandler),
        (r'/{}/api/u/(.*)/documents/reupload'.format(users_base_name), users.ApiReuploadDocumentHandler),
        (r'/{}/api/u/(.*)/email/validate/(.*)'.format(users_base_name), users.ApiValidateEmail),
        (r'/{}/api/u/(.*)/email/validate'.format(users_base_name), users.ApiValidateEmail),
        (r'/{}/api/u/(.*)/password/change'.format(users_base_name), users.ApiChangePasswordHandler),
        (r'/{}/api/u/(.*)/password/change/token/(.*)'.format(users_base_name),
         users.ApiChangePasswordHandler),
        (r'/{}/u/(.*)'.format(users_base_name), users.UserPageHandler),
        (r'/{}'.format(users_base_name), users.HomeHandler),
        (r'/{}/'.format(users_base_name), users.HomeHandler),

        # ATTENDANCE

        (r'/{}/u/(.*)/date/(.*)'.format(attendance_base_name), attendance.UserAttendancePageHandler),
        (r'/{}/u/(.*)'.format(attendance_base_name), attendance.UserAttendancePageHandler),
        (r'/{}/api/u/(.*)/workspans/add'.format(attendance_base_name), attendance.ApiAddWorkspanHandler),
        (r'/{}/api/u/(.*)/workspans/edit_month'.format(attendance_base_name), attendance.ApiEditMonthWorkspansHandler),
        (r'/{}/api/u/(.*)/workspans/delete'.format(attendance_base_name), attendance.ApiDeleteWorkspanHandler),
        (r'/{}/api/u/(.*)/calendar/date/(.*)'.format(attendance_base_name), attendance.ApiCalendarHandler),
        (r'/{}/api/u/(.*)/monthinfo/date/(.*)'.format(attendance_base_name), attendance.ApiMonthInfoHandler),
        (r'/{}/api/u/(.*)/vacations/add'.format(attendance_base_name), attendance.ApiAddVacationHandler),
        (r'/{}/api/u/(.*)/vacations/interrupt'.format(attendance_base_name), attendance.ApiInterruptVacationHandler),
        (r'/{}/api/u/(.*)/close_month'.format(attendance_base_name), attendance.ApiCloseMonthHandler),
        (r'/{}/api/u/(.*)/reopen_month'.format(attendance_base_name), attendance.ApiReopenMonthHandler),
        (r'/{}/api/month_table/date/(.*)'.format(attendance_base_name), attendance.ApiAdminMonthTableHandler),
        (r'/{}/api/year_table/date/(.*)'.format(attendance_base_name), attendance.ApiAdminYearTableHandler),
        (r'/{}/api/reports_table/date/(.*)'.format(attendance_base_name), attendance.ApiAdminReportsTableHandler),
        (r'/{}/api/reports/accountant/generate'.format(attendance_base_name),
         attendance.ApiGenerateAccountantReportHandler),
        (r'/{}/api/reports/hours_worked/generate'.format(attendance_base_name),
         attendance.ApiGenerateHoursWorkedReportHandler),
        (r'/{}'.format(attendance_base_name), attendance.HomeHandler),
        (r'/{}/'.format(attendance_base_name), attendance.HomeHandler),
    ]


def get_plugin_info():
    return {
        "module": "users",
        "name": "Uživatelé",
        "icon": 'icon_users.svg'
    }
