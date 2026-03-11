# ######################################################################################
# ExportWorker is basically the worker thread of ExportManager
# basically a threaded way of calling backend.ImageSession's export_final  
# ######################################################################################

from PySide6.QtCore import QObject, Signal, Slot
import traceback
from ...backend.ImageSession import ImageSession

class ExportWorker(QObject):
    """
    Runs the export_final in imagesession export process in a background thread.
    Communicates results back to the Main Thread via Signals.
    """
    finished = Signal(bool, str) # Success (True/False), Message

    def __init__(self, session:ImageSession, path:str):
        super().__init__()
        self.session = session
        self.path = path

    @Slot()
    def run(self):
        """ Is started  by ui.ExportManager  
            calls backend.ImageSession's export_final method to do the work 
            whihc in turn calls backend.engines.Exportengine

        """
        try:
            # Safety check: if session was scrubbed before thread started
            if not self.session:
                self.finished.emit(False, "Export failed: No active session.")
                return

            # This blocking call now runs in the background thread
            # Ensure session.export_final regularly checks an internal abort flag
            self.session.export_final(self.path)
            
            # If we reach here, and the session wasn't aborted midway
            self.finished.emit(True, "Export Completed Successfully")
            
        except InterruptedError:
            self.finished.emit(False, "Export Cancelled On User's Request")
            
        except TimeoutError:
            self.finished.emit(False, "Export Failed: Operation Timed Out")
            
        except MemoryError:
            self.finished.emit(False, "Export Failed: System Memory Critical")
            
        except Exception as e:
            # Print full trace to console for debugging
            traceback.print_exc()
            self.finished.emit(False, f"Error: {str(e)}")
        
        # Do not perform cleanup here , call it from outside 
        # session is needed in case user cancels the export 
        #finally:
            # Ensure references are dropped even if an exception occurs
            #print("Worker cleanup ...!!")
            # self.cleanup() 

    @Slot()
    def cancel(self):
        """
        Slot called by the Overlay when user hits Cancel/Esc.
        """
        # We check both session and its internal state to signal abortion
        if self.session:
            # This triggers the flag that your backend tiling loop should check
            print("Exportworker: self.session.request_abort_export()")
            self.session.request_abort_export()
            
        else:
            print("ExportWorker:  Abort requested but no session set! ")    

    def cleanup(self):
        """Explicitly break links to large objects. We remeber to call this to clear all refs"""
        # Nullifying the session is the critical step to free the 150MB+ buffer
        self.session = None
        # Clearing engine references if any were passed or created
        if hasattr(self, 'render_engine'):
            self.render_engine = None
        if hasattr(self, 'mask_engine'):
            self.mask_engine = None
            
            