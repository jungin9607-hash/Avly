"""판례 조회 (M5에서 완성). 지금은 아무것도 돌려주지 않는다."""


def make_cases(repo, engine):
    from app.worker.runner import NoCases
    return NoCases()
