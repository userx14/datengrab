import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class DatengrabMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        OuterVBox = QVBoxLayout()
        OuterVBox.addLayout(self.init_searchBoxUI(), 0)
        OuterVBox.addSpacerItem(QSpacerItem(0,20))
        OuterVBox.addLayout(self.init_fileAndTagUI(),1)
        
        self.setLayout(OuterVBox)
        self.setWindowIcon(QIcon('datengrab.png'))
        self.setWindowTitle("datengrab v1")
        self.setAcceptDrops(True)
        self.show()
        #
        #self.setCentralWidget(tagSearchInputLineEdit)
    
    def init_searchBoxUI(self):
        #tag searchbox and label
        tagSearchVBox_label = QLabel("tag filter:")
        tagSearchVBox_LineEdit = QLineEdit()
        tagSearchVBox_LineEdit.setPlaceholderText("tag1 & (!tag2) | tag3")
        
        tagSearchVBox = QVBoxLayout()
        tagSearchVBox.addWidget(tagSearchVBox_label, 1,  Qt.AlignLeft)
        tagSearchVBox.addWidget(tagSearchVBox_LineEdit)
        
        #file searchbox and label
        fileSearchVBox_label = QLabel("file properties filter:")
        fileSearchVBox_LineEdit = QLineEdit()
        fileSearchVBox_LineEdit.setPlaceholderText("name = *.pdf & date < 2021")
        
        fileSearchVBox = QVBoxLayout()
        fileSearchVBox.addWidget(fileSearchVBox_label,  Qt.AlignLeft)
        fileSearchVBox.addWidget(fileSearchVBox_LineEdit)
        
        fileSearchInputLineEdit = QLineEdit()
        fileSearchInputLineEdit.setPlaceholderText("file selection string like (name = *.pdf)")
        
        
        #progress indicator
        progressBar = QProgressBar()
        progressBar.setRange(0, 0)
        #search button
        searchPushButton = QPushButton("Search")
        
        progressAndButton = QVBoxLayout()
        progressAndButton.addWidget(progressBar)
        progressAndButton.addWidget(searchPushButton)
        progressAndButton.setHoriz
        
        #upper layout row for search functionality
        searchHBox = QHBoxLayout()
        searchHBox.addLayout(tagSearchVBox, 1)
        searchHBox.addLayout(fileSearchVBox, 1)
        searchHBox.addLayout(progressAndButton, 0)
        return searchHBox
        
    def init_fileAndTagUI(self):
        #current files
        filesLabel = QLabel("files (drag- & drop-able)")

        filesTable = QTableWidget()
        
        filesVbox = QVBoxLayout()
        filesVbox.addWidget(filesLabel)
        filesVbox.addWidget(filesTable)
        
        
        #common tags
        commonTagsLabel = QLabel("common tags of files")
        
        commonTagsTree = QTreeView()

        commonTagsVbox = QVBoxLayout()
        commonTagsVbox.addWidget(commonTagsLabel)
        commonTagsVbox.addWidget(commonTagsTree)
        
        
        #all tags
        allTagsLabel = QLabel("all tags")
        
        allTagsTree = QTreeView()
        
        allTagsVBox = QVBoxLayout()
        allTagsVBox.addWidget(allTagsLabel)
        allTagsVBox.addWidget(allTagsTree)
        
        
        #vbox for common and all tags
        TagsVBox = QVBoxLayout()
        TagsVBox.addLayout(commonTagsVbox)
        TagsVBox.addLayout(allTagsVBox)
        
        #hbox for tags and files
        TagsAndFilesHBox = QHBoxLayout()
        TagsAndFilesHBox.addLayout(filesVbox)
        TagsAndFilesHBox.addLayout(TagsVBox)
        
        return TagsAndFilesHBox
        
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            print(f)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
def main():
    app = QApplication(sys.argv)
    window = DatengrabMainWindow()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()