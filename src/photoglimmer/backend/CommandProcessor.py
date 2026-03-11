# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# Part of the Command Pattern
# Important--  All command execution is delegated here 
#              the push() function below is where a commad actually gets executed!  
#  
# ######################################################################################


#with optimization for memory etc
class CommandProcessor:
    MAX_UNDO = 10   

    def __init__(self):
        self.undo_stack, self.redo_stack = [], []

    def push(self, cmd):
        cmd.execute()
        self.undo_stack.append(cmd)
        
        
        # If we exceed the limit, the oldest command is removed from memory
        if len(self.undo_stack) > self.MAX_UNDO:
            oldest_cmd = self.undo_stack.pop(0) # Remove from the bottom
            self._cleanup_command(oldest_cmd)
            
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            cmd = self.undo_stack.pop()
            cmd.undo()
            self.redo_stack.append(cmd)

    def redo(self):
        if self.redo_stack:
            cmd = self.redo_stack.pop()
            cmd.execute()
            self.undo_stack.append(cmd)

    def _cleanup_command(self, cmd):
        """Triggers the high-res memory release if the command supports it."""
        if hasattr(cmd, 'on_evicted_from_undo_stack'):
            try:
                cmd.on_evicted_from_undo_stack()
            except Exception as e:
                # Log but don't crash the UI during cleanup
                print(f"Cleanup Error: {e}")

    def clear(self):
        """Full flush for ImageSession.close()"""
        for cmd in self.undo_stack:
            self._cleanup_command(cmd)
        for cmd in self.redo_stack:
            self._cleanup_command(cmd)
        self.undo_stack.clear()
        self.redo_stack.clear()

    def can_undo(self): return len(self.undo_stack) > 0
    def can_redo(self): return len(self.redo_stack) > 0
