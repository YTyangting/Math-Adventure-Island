# from django.contrib import admin
from django.urls import path

from api.views import login, problem, report
from api.views import add_table

urlpatterns = [
    path('login/', login.LoginView.as_view()),
    path('sign/', login.SignView.as_view()),
    path('problemset/', problem.ProblemsetView.as_view()),
    path('intell_analy/',problem.IntelAnalyView.as_view()),
    path('problemUpload/', problem.ProblemUploadView.as_view()),
    path('testProblemUpload/', problem.TestProblemUploadView.as_view()),
    path('addProblemTable/', add_table.AddProblemTable.as_view()),
    path('problemExecute/', problem.ProblemExecuteView.as_view()),
    path('testProblemExecute/', problem.TestProblemExecuteView.as_view()),
    path('aceProblemExecute/', problem.AceProblemExecuteView.as_view()),
    path('testRecords/', problem.TestRecordsView.as_view()),
    path('report/', report.ReportView.as_view()),
    path('reportConcept/', report.ReportConceptView.as_view()),
    path('clockCardInfo/', report.ClockCardInfoView.as_view()),
    path('simulationProbNid/', report.SimulationProbNidView.as_view()),
]
