
# source for all the code in  this file :
# https://gist.github.com/sabapathygithub/160ecf262063bcb826787a7af1637f44
from PySide2.QtCore import QObject,QRunnable,QThreadPool
from PySide2.QtCore import Signal as pyqtSignal
from PySide2.QtCore import Slot as pyqtSlot
import sys,traceback


class  WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int, str)


class  Worker(QRunnable):


    def  __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress
    @pyqtSlot()


    def  run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  
        finally:
            self.signals.finished.emit()  


class  Tasks(QObject):
    result: object


    def  __init__(self):
        super(Tasks, self).__init__()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(1)
        self.signals = WorkerSignals()


    def  process_result(self, result):
        self.signals.result.emit(result)


    def  start(self, process_fn, *args):
        worker = Worker(process_fn, *args)
        worker.signals.result.connect(self.process_result)
        self.pool.start(worker)