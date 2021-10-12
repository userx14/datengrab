import sqlite3Backend as datengrabSql
import os, time, sys, datetime
from pathlib import Path
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from sqlite3Backend import getTagHierarchy
import sqlite3Backend
from sympy.physics.units.definitions.dimension_definitions import current

datengrab_filedumpFolder = "datengrab"

class DatengrabFileTable(QTableWidget):
    tableColumnNames = ["filename", "size", "last changed"]
    
    def __init__(self, mainClassReference):
        super().__init__()
        self.mainClassReference = mainClassReference
        self.setSortingEnabled(True)
        self.setHorizontalHeaderLabels(self.tableColumnNames)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.verticalHeader().setVisible(False)    
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(self.tableColumnNames)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.setDragDropOverwriteMode(False) #do not overwrite items with data from drag drop 
        self.setAcceptDrops(True)
        self.selectionModel().selectionChanged.connect(self.on_selectionChanged)
    
    def getSelectedRowsList(self):
        selectedRowNumbers = [index.row() for index in self.selectionModel().selectedRows()]
        return selectedRowNumbers
    
    def getSelectedFilesList(self):
        return [self.item(row, 0).text() for row in self.getSelectedRowsList()]
    
    def on_selectionChanged(self, selected, diselected):
        tagsOfSelectionDict = dict()
        for fileName in self.getSelectedFilesList():
            tagNames = self.mainClassReference.filesTagsDict[fileName]
            for tagName in tagNames:
                tagsOfSelectionDict[tagName] = tagsOfSelectionDict.get(tagName, 0) + 1
        self.mainClassReference.selectionTagsTable.setDataFromDict(tagsOfSelectionDict)
        
    def updateDataFromMainClass(self):
        FileNamesStringList = self.mainClassReference.filesList
        self.setRowCount(len(FileNamesStringList))
        self.fileNamesList = FileNamesStringList
        for rowIdx in range(len(FileNamesStringList)):
            fileName = FileNamesStringList[rowIdx]
            try:
                filestat = os.stat("./"+datengrab_filedumpFolder+"/"+fileName)
            except Exception:
                print("error")
                self.setItem(rowIdx, 0, QTableWidgetItem(fileName))
                self.setItem(rowIdx, 1, QTableWidgetItem("error"))
                self.setItem(rowIdx, 2, QTableWidgetItem("error"))
                continue
            print(filestat)
            nameWidget = QTableWidgetItem(fileName)
            nameWidget.setFlags(nameWidget.flags() & (~Qt.ItemIsEditable))
            
            sizeWidget = QTableWidgetItem(str(filestat.st_size))
            sizeWidget.setFlags(sizeWidget.flags() & (~Qt.ItemIsEditable))
            
            dateTimeWidget = QTableWidgetItem(datetime.datetime.utcfromtimestamp(int(filestat.st_mtime)).strftime('%Y-%m-%d %H:%M:%S'))
            dateTimeWidget.setFlags(dateTimeWidget.flags() & (~Qt.ItemIsEditable))

            self.setItem(rowIdx, 0, nameWidget)
            self.setItem(rowIdx, 1, sizeWidget)
            self.setItem(rowIdx, 2, dateTimeWidget)
            #set row selected
        self.selectAll()
        
        
    def contextMenuEvent(self, event):
        
        if(not self.currentItem()):
            return
        filename = self.item(self.currentItem().row(), 0).text()
        tagContextMenu = QMenu(self)
        renameAction = tagContextMenu.addAction("Rename")
        deleteAction = tagContextMenu.addAction("Delete")
        action = tagContextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == renameAction:
            print(self.currentItem().text())
            print("rename")
        elif action == deleteAction:
            print("delete")
        else:
            print("Error")
       
    def dropEvent(self, event):
        if(event.mimeData().hasUrls() and (not event.mimeData().hasFormat("app/fileList"))):
            print("has urls and is not from this app")
            event.accept()
            filePaths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
            for filePath in filePaths:
                print(f"addfile {filePath}")
                sqlite3Backend.importFile(filePath)
        else:
            event.ignore()
            print("ignored drop event")
    
    def dragEnterEvent(self, event):
        if(event.mimeData().hasUrls() and (not event.mimeData().hasFormat("app/fileList"))):
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if(event.mimeData().hasUrls() and (not event.mimeData().hasFormat("app/fileList"))):
            event.accept()
        else:
            event.ignore()
        
    def startDrag(self, *args, **kwargs):
        itemRows = list(dict.fromkeys([item.row() for item in self.selectedItems()]))
        print(itemRows)
        
        mimeData = QMimeData()
        pwd = os.getcwd()
        filePaths = [str(pwd) +"/"+ datengrab_filedumpFolder + "/" + filename for filename in self.fileNamesList]
        fileUrls = [QUrl().fromLocalFile(filepath) for filepath in filePaths]
        print(fileUrls)
        mimeData.setUrls(fileUrls)
        mimeData.setData("app/fileList", QByteArray()) #make drag detectable so we can block it from being droppen back into the files window
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        #drag.exec_(Qt.MoveAction) for move instead of copy
        drag.exec_(Qt.CopyAction)
        print("Start drag")
     
    

class DatengrabAllTagsTree(QTreeWidget):
    def __init__(self, mainClassReference):
        super().__init__()
        self.setColumnCount(1)
        self.setDragEnabled(True)
        self.getDataFromBackend()
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        #self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mainClassReference = mainClassReference
        #connect(self, SIGNAL(customContextMenuRequested(QPoint)), SLOT(customMenuRequested(QPoint)));)
    
    def contextMenuEvent(self, event):
        tagContextMenu = QMenu(self)
        addAction = tagContextMenu.addAction("Add child tag")
        renameAction = tagContextMenu.addAction("Rename")
        deleteAction = tagContextMenu.addAction("Delete")
        action = tagContextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == addAction:
            print("add")
        elif action == renameAction:
            print("rename")
        elif action == deleteAction:
            print("delete")
        else:
            print("Error")
    
    def getDataFromBackend(self):
        self.clear()
        tagHierarchy = datengrabSql.getTagHierarchy()
        topLevelItem = self.recursiveTreeWidgetFill(tagHierarchy)
        self.addTopLevelItem(topLevelItem)
        
    def recursiveTreeWidgetFill(self, currentTagInHierarchy):
        newChild = QTreeWidgetItem()
        newChild.setText(0, currentTagInHierarchy.name)
        for subTag in sorted(currentTagInHierarchy.childs, key=lambda x: x.name):
            newChild.addChild(self.recursiveTreeWidgetFill(subTag))
        return newChild
    
    def dropEvent(self, event):
        droppedOnQIndex = self.indexAt(event.pos())
        droppedOnTagName = droppedOnQIndex.data()
        print(droppedOnTagName)
        mimeData = event.mimeData()
        #check that mime data is a tag,   that the dropped tag is not the root tag,    and that the drop target is a valid tag in the tree view
        if(mimeData.hasFormat("app/tagName") and mimeData.hasFormat("app/parentTagName") and droppedOnTagName):
            tagName = str(mimeData.data("app/tagName"), 'utf-8')
            parentTagName = str(mimeData.data("app/parentTagName"), 'utf-8')
            #check that tag can not be dropped on itself
            if(droppedOnTagName != parentTagName):
                #make sure one can't tag one tree onto one of it's deeper nested childs or itself
                droppedOnIsNotChild = True;
                currentCheckedTagInHierarchy = droppedOnQIndex
                while(currentCheckedTagInHierarchy.data() != None):
                    if(currentCheckedTagInHierarchy.data() == tagName):
                        droppedOnIsNotChild = False
                        break;
                    currentCheckedTagInHierarchy = currentCheckedTagInHierarchy.parent()
                    print(currentCheckedTagInHierarchy.data())
                if(droppedOnIsNotChild):
                    event.accept()
                    sqlite3Backend.moveExistingTagToNewParent(tagName, droppedOnTagName)
                    self.getDataFromBackend()
                    return
        event.ignore()
        return
    
    def dragEnterEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        droppedOnQIndex = self.indexAt(event.pos())
        droppedOnTagName = droppedOnQIndex.data()
        print(droppedOnTagName)
        mimeData = event.mimeData()
        #avoid dropping on same element or parent of current element
        if(mimeData.hasFormat("app/tagName") and mimeData.hasFormat("app/parentTagName") and droppedOnTagName):
            tagName = str(mimeData.data("app/tagName"), 'utf-8')
            parentTagName = str(mimeData.data("app/parentTagName"), 'utf-8')
            #check that tag can not be dropped on itself
            if(droppedOnTagName != parentTagName):
                #make sure one can't tag one tree onto one of it's deeper nested childs or itself
                droppedOnIsNotChild = True;
                currentCheckedTagInHierarchy = droppedOnQIndex
                while(currentCheckedTagInHierarchy.data() != None):
                    if(currentCheckedTagInHierarchy.data() == tagName):
                        droppedOnIsNotChild = False
                        break;
                    currentCheckedTagInHierarchy = currentCheckedTagInHierarchy.parent()
                    print(currentCheckedTagInHierarchy.data())
                if(droppedOnIsNotChild):
                    event.accept()
                    return
        event.ignore()
        return
        return
    
    def startDrag(self, *args, **kwargs):
        mimeData = QMimeData()
        mimePayloadTagName = QByteArray(bytes(self.currentItem().text(0), encoding='utf8'))
        mimeData.setData("app/tagName", mimePayloadTagName)
        if(self.currentItem().parent() != None): #root tag has no parent
            mimePayloadParentTagName = QByteArray(bytes(self.currentItem().parent().text(0), encoding='utf8'))
            mimeData.setData("app/parentTagName", mimePayloadParentTagName)
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(Qt.MoveAction)
        print("tag drag")
    
class DatengrabSelectionTagsTable(QTableWidget):
    
    tableColumnNames = ["tagname", "num of selectecd files with this tag", "remove tag from selection"]
    
    def __init__(self, mainClassReference):
        super().__init__()
        self.setColumnCount(3)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setHorizontalHeaderLabels(self.tableColumnNames)
        self.verticalHeader().setVisible(False)
        self.setAcceptDrops(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.mainClassReference = mainClassReference

    
    def dropEvent(self, event):
        mimeData = event.mimeData()
        if(mimeData.hasFormat("app/tagName")):
            tagName = str(mimeData.data("app/tagName"), 'utf-8')
            event.accept()
            
            selectedFilesList = self.mainClassReference.fileTable.getSelectedFilesList()
            for fileName in selectedFilesList:
                print(f"adding tag {tagName} to {fileName}")
                sqlite3Backend.addTagToFile(fileName, tagName)
                self.mainClassReference.filesTagsDict[fileName] = sqlite3Backend.findTagsOfFile(fileName) #update tags of file
            self.mainClassReference.fileTable.on_selectionChanged(None, None)
            return
        event.ignore()
    
    def dragEnterEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()
    
    def setDataFromDict(self, tagNameAndOcurrencesDict):
        tagsDict = tagNameAndOcurrencesDict
        self.setRowCount(len(tagsDict))
        for index, (key, value) in enumerate(tagsDict.items()):
            tagNameItem = QTableWidgetItem(key)
            tagNameItem.setFlags(tagNameItem.flags() & (~Qt.ItemIsEditable))
            self.setItem(index, 0, tagNameItem)
            tagCountItem = QTableWidgetItem(str(value))
            tagCountItem.setFlags(tagCountItem.flags() & (~Qt.ItemIsEditable))
            self.setItem(index, 1, tagCountItem)
            self.setIndexWidget(self.model().index(index, 3), QPushButton("remove from sel"))


class DatengrabTagSearchLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        
        
    def dropEvent(self, event):
        mimeData = event.mimeData()
        if(mimeData.hasFormat("app/tagName")):
            tagName = str(mimeData.data("app/tagName"), 'utf-8')
            event.accept()
            oldTextboxContent = self.text()
            print(f"here :{oldTextboxContent}")
            print(type(oldTextboxContent))
            if(not oldTextboxContent):
                self.setText(tagName)
            elif(oldTextboxContent[-1] == " "):
                self.setText(oldTextboxContent + tagName)
            else:
                self.setText(oldTextboxContent + " " + tagName)
            return
        event.ignore()
    
    def dragEnterEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()

class DatengrabMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        GridLayout = QGridLayout()
        GridLayout.addLayout(self.init_tagSearchBox(), 0, 0)
        GridLayout.addLayout(self.init_fileSearchBoxAndExecuteButton(), 0, 1)
        GridLayout.setRowStretch(0, 0)
        
        GridLayout.addLayout(self.init_AllAndSelectedTagUI(), 1, 0)
        GridLayout.addLayout(self.init_FileUI(), 1, 1)
        GridLayout.setRowStretch(1, 1)
        
        self.setLayout(GridLayout)
        self.setWindowIcon(QIcon('datengrab.png'))
        self.setWindowTitle("datengrab v1")
        self.show()
    
    def init_tagSearchBox(self):
        #tag searchbox and label
        tagSearchVBox_label = QLabel("tag filter: (tag drop sink)")
        tagSearchVBox_LineEdit = DatengrabTagSearchLineEdit()
        tagSearchVBox_LineEdit.setPlaceholderText("tag1 & (!tag2) | tag3")
        self.tagSearchLineEdit = tagSearchVBox_LineEdit
        
        tagSearchVBox = QVBoxLayout()
        tagSearchVBox.addWidget(tagSearchVBox_label, 1,  Qt.AlignLeft)
        tagSearchVBox.addWidget(tagSearchVBox_LineEdit)
        return tagSearchVBox
    
    def init_fileSearchBoxAndExecuteButton(self):
        #file searchbox and label
        fileSearchVBox_label = QLabel("file properties filter:")
        fileSearchVBox_LineEdit = QLineEdit()
        fileSearchVBox_LineEdit.setPlaceholderText("fileName in [\"doc.pdf\"] & fileDate < 2021")
        self.fileSearchLineEdit = fileSearchVBox_LineEdit
        
        fileSearchVBox = QVBoxLayout()
        fileSearchVBox.addWidget(fileSearchVBox_label,  Qt.AlignLeft)
        fileSearchVBox.addWidget(fileSearchVBox_LineEdit)
        
        fileSearchInputLineEdit = QLineEdit()
        fileSearchInputLineEdit.setPlaceholderText("file selection string like (name = *.pdf)")
        
        #progress indicator
        progressBar = QProgressBar()
        progressBar.setTextVisible(False)
        self.progressBar = progressBar
        self.progressBarAnimateStop()
        
        #search button
        searchPushButton = QPushButton("Search")
        searchPushButton.clicked.connect(self.startSearch)
        
        progressAndButton = QVBoxLayout()
        progressAndButton.addWidget(progressBar)
        progressAndButton.addWidget(searchPushButton)
        
        combinedHbox = QHBoxLayout()
        combinedHbox.addLayout(fileSearchVBox)
        combinedHbox.addLayout(progressAndButton)
        combinedHbox.setStretch(0, 1)
        combinedHbox.setStretch(1, 0)
        return combinedHbox
        

    def init_AllAndSelectedTagUI(self):
        #tags of selection
        selectionTagsLabel = QLabel("tags of selected files (tag drop sink)")
        
        self.selectionTagsTable = DatengrabSelectionTagsTable(self)

        selectionTagsVbox = QVBoxLayout()
        selectionTagsVbox.addWidget(selectionTagsLabel)
        selectionTagsVbox.addWidget(self.selectionTagsTable)
        
        #all tags
        allTagsLabel = QLabel("all tags hierarchy (tag drag source & tag drop sink)")
        
        self.allTagsTree = DatengrabAllTagsTree(self)
        
        allTagsVBox = QVBoxLayout()
        allTagsVBox.addWidget(allTagsLabel)
        allTagsVBox.addWidget(self.allTagsTree)
        
        #vbox for selected and all tags
        TagsVBox = QVBoxLayout()
        TagsVBox.addLayout(selectionTagsVbox)
        TagsVBox.addLayout(allTagsVBox)
        
        return TagsVBox
        
    def init_FileUI(self):
        #current files
        filesLabel = QLabel("files (file drag source & file drop sink)")
        self.fileTable = DatengrabFileTable(self)
        
        filesVbox = QVBoxLayout()
        filesVbox.addWidget(filesLabel)
        filesVbox.addWidget(self.fileTable)
        
        return filesVbox
    
    def progressBarAnimateStart(self):
        self.progressBar.setRange(0, 0)
    
    def progressBarAnimateStop(self):
        self.progressBar.setRange(0, 100)  
        
    def startSearch(self):
        self.progressBarAnimateStart()
        #set default color palette
        self.tagSearchLineEdit.setPalette(QPalette())
        self.fileSearchLineEdit.setPalette(QPalette())
        
        tagSearchString = self.tagSearchLineEdit.text()
        fileSearchString = self.fileSearchLineEdit.text()
        
        try:
            potentialFilesWithTagList = datengrabSql.findFilesWithTags(tagSearchString)
        except ValueError:
            lineEditErrorPalette = QPalette()
            lineEditErrorPalette.setColor(QPalette.Base, Qt.red)
            self.tagSearchLineEdit.setPalette(lineEditErrorPalette)
            self.progressBarAnimateStop()
            return
        
        #todo handle file search (name, date, ...)
        
        
        self.filesList = potentialFilesWithTagList
        self.filesTagsDict = dict()
        for filename in self.filesList:
            self.filesTagsDict[filename] = sqlite3Backend.findTagsOfFile(filename)
        
        
        self.fileTable.updateDataFromMainClass()
        self.progressBarAnimateStop()
    
    def dragEnterEvent(self, event):
        event.accept()


        
    
  
def main():
    app = QApplication(sys.argv)
    app.setStyle("Windows")
    window = DatengrabMainWindow()
    window.resize(1280, 720)
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()