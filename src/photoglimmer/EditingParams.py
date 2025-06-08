
# ###############################################################################
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.
# ###############################################################################
# Parameters for Editing 
# These are different form parameters for image layers
# and determine  how editng is to be done , instead of per layer values
# TODO: some parts like isSegmentationNeeded to be fully transferrwed here


class  EditingParams:


    def  init(self):
        self.isLUTMode= False
        self.isTweakNeeded=True
        self.isSegmentationNeeded=False;


    def  setLUTMode(self,b:bool):
        self.isLUTMode= b


    def  setTweakNeeded(self,b:bool):
        self.isTweakNeeded= b


    def  setSegmentationNeeded(self,b:bool):
        self.isSegmentationNeeded= b