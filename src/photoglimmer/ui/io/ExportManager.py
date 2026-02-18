# #####################################################################################
# Orchestrates the final export rendering of full sized images      
# as well as final file saving in a asynchronous manner
# Also manages the display of spinner overlay while the log render thread and save  runs
# has a Qthread which it attaches to ExportWorker , 
# which in turn calls Imagession's export_final,
# which then calls backends.ExportRenderEngine's run 
#######################################################################################

from PySide6.QtCore import QObject, QThread, Slot
from ..components.CustomDialog import CustomDialog
from ..components.ExportWorker import ExportWorker
import gc

class ExportManager(QObject):
    """
    Calls export rendering as well as does final saving 
    Manages the asynchronous export workflow.
    Located in 'ui/io' because it handles File Output coordination.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.session = None
        self.worker = None
        self.thread = None # a Qthread which will be mapped to ExportWorker

    def set_session(self, session):
        self.session = session
        

    def start_export(self, output_path):
        if not self.session: return

        self.main_window.show_status("Exporting high-res image...", 0)
        
        # 1. Setup
        self.thread = QThread()
        self.worker = ExportWorker(self.session, output_path)
        self.worker.moveToThread(self.thread)

        # 2. Connect Signals
        self.thread.started.connect(self.worker.run)
        
        # Proper cleanup sequence: Worker finishes -> Thread quits -> Both delete
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self._on_export_finished)
        
        # Use deleteLater to let Qt handle C++ deallocation safely
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.destroyed.connect(lambda: print("Worker C++ object destroyed"))

        # if hasattr(self.main_window, 'overlay'):
        #     self.main_window.overlay.canceled.connect(self.worker.cancel)

        # 3. Lock UI & Start
        self.main_window.toggle_canvas_dimming(True)
        self.main_window.overlay.start()
        self.thread.start()

    @Slot(bool, str)
    def _on_export_finished(self, success, message):
        """Runs when ExportWorker finishes. Responsible for showing Dialog as per worker's result"""
        # TODO: send dialog showing to mainwindow  
        if hasattr(self.main_window, 'overlay'):
            self.main_window.overlay.stop()

        self.main_window.toggle_canvas_dimming(False)

        if success:
            #self.main_window.show_status("File Saved Successfully", 6000)
            CustomDialog.info(self.main_window, "File Saved", message)
        elif "Cancelled" in message:
            CustomDialog.info(self.main_window, "Export Cancelled", message)
        else:
            CustomDialog.error(self.main_window, "Export Failed", message)
        
        self.cleanup()

    

    def cleanup(self):
        """ The SINGLE source of truth for clearing export memory.
            We have to be extra careful with exceptions during abort because we are dealing with objects 
            originating in C++ layer of opencv , and fomr outside the thread's context         
        """
        
        # 1. Thread Safety: Check if the C++ object still exists
        # Wrapping it in a try/except
        try:
            if self.thread:
                if self.thread.isRunning():
                    if self.worker:
                        self.worker.cancel()
                    
                    self.thread.quit()
                    if not self.thread.wait(2000):
                        self.thread.terminate()
                        self.thread.wait()
                
                # Manually trigger deletion now that we are done with it
                self.thread.deleteLater()
        except RuntimeError:
            # Thread already deleted by Qt, safe to ignore
            pass

        # 2. Sever references
        if self.worker:
            try:
                self.worker.finished.disconnect()               
                
            except: pass
            self.worker.cleanup()
            self.worker.session = None

        
        self.worker = None
        self.thread = None
        self.session = None
        
        gc.collect()
        #print("ExportManager: Cleanup successful.")

        