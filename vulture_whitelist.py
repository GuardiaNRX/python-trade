whitelist = set([
    "backtests.report_daily:main",
    "scripts.canary:main",
    "scripts.smoke_replay:main",
    "scripts.janitor:main",
    # API używane przez importy dynamiczne
    "utils.exec_policy:plan_twap",
    "utils.broker:PaperBroker",
    "utils.run_status:start_run",
    "utils.run_status:finalize_run",
])
