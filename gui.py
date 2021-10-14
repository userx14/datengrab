import sqlite3Backend as datengrabSql
import os, time, sys, datetime
from pathlib import Path
from os import path
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from sqlite3Backend import getTagHierarchy, filestorage_location
import sqlite3Backend
from fileinput import filename

class DatengrabFileDeleteDialog(QDialog):
    def __init__(self, fileName):
        super().__init__()
        self.setWindowTitle("datengrab - warning - file deletion")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.deleteFile)
        self.buttonBox.rejected.connect(self.closeBox)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"You are about to delete the file {fileName} from the disk and the database, continue?"))
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    def deleteFile(self):
        self.done(1)
    def closeBox(self):
        self.done(0)

class DatengrabTagDeleteDialog(QDialog):
    def __init__(self, tagName):
        super().__init__()
        self.setWindowTitle("datengrab - warning - tag deletion")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.deleteFile)
        self.buttonBox.rejected.connect(self.closeBox)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"You are about to delete the tag {tagName} and all it's child tags from the database, continue?"))
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    def deleteFile(self):
        self.done(1)
    def closeBox(self):
        self.done(0)


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
        self.itemChanged.connect(self.filenameEditComplete)
        self.itemDelegate().closeEditor.connect(self.editClosed)

    def editClosed(self):
        #deactivate editing after edit mode is closed
        self.lastItemInEditMode.setFlags(self.lastItemInEditMode.flags() & (~Qt.ItemIsEditable))
    
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
        self.itemChanged.disconnect()
        FileNamesStringList = self.mainClassReference.filesList
        self.setRowCount(len(FileNamesStringList))
        self.fileNamesList = FileNamesStringList
        for rowIdx in range(len(FileNamesStringList)):
            fileName = FileNamesStringList[rowIdx]
            try:
                filestat = os.stat(Path().cwd() / filestorage_location / fileName)
            except Exception:
                print("error")
                self.setItem(rowIdx, 0, QTableWidgetItem(fileName))
                self.setItem(rowIdx, 1, QTableWidgetItem("error - not found on disk"))
                self.setItem(rowIdx, 2, QTableWidgetItem("error - not found on disk"))
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
        self.itemChanged.connect(self.filenameEditComplete)

    def filenameEditComplete(self, item):
        if(self.state() == QAbstractItemView.EditingState):
            newFilename = item.text()
            oldFilename = self.lastEditedFilename
            print(f"renaming {oldFilename} to {newFilename}")
            sqlite3Backend.renameFile(oldFilename, newFilename)
            filesList = self.mainClassReference.filesList
            filesList[filesList.index(oldFilename)] = newFilename
            filesTagsDict = self.mainClassReference.filesTagsDict
            filesTagsDict[newFilename] = filesTagsDict.pop(oldFilename)
        else:
            self.lastEditedFilename = item.text()

    def contextMenuEvent(self, event):

        if(not self.currentItem()):
            return
        currentRow = self.currentItem().row()
        fileNameItem =  self.item(currentRow, 0)
        fileName = fileNameItem.text()
        tagContextMenu = QMenu(self)
        renameAction = tagContextMenu.addAction("rename")
        deleteAction = tagContextMenu.addAction("delete")
        action = tagContextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == renameAction:
            self.lastItemInEditMode = fileNameItem
            print(fileNameItem.text())
            #enable editing and force to enter edit mode
            fileNameItem.setFlags(fileNameItem.flags() | Qt.ItemIsEditable)
            self.editItem(self.item(currentRow, 0))
        elif action == deleteAction:
            print(f"delete file {fileName}")
            deletionConfirmed = DatengrabFileDeleteDialog(fileName).exec_()
            if deletionConfirmed:
                sqlite3Backend.deleteFileAndItsTags(fileName)
                self.mainClassReference.filesList.remove(fileName)
                self.mainClassReference.filesTagsDict.pop(fileName)
                self.removeRow(currentRow)
        else:
            print(f"Error unknown action of context menu: {action}")

    def dropEvent(self, event):
        if(event.mimeData().hasUrls() and (not event.mimeData().hasFormat("app/fileList"))):
            print("has urls and is not from this app")
            event.accept()
            filePaths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
            for filePath in filePaths:
                print(f"addfile {filePath}")
                sqlite3Backend.importFile(filePath)
            fileNames = [filePath.name for filePath in filePaths]
            self.mainClassReference.filesList = fileNames
            self.mainClassReference.filesTagsDict.clear()
            for fileName in fileNames:
                self.mainClassReference.filesTagsDict[fileName] = []
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
        filePaths = [Path.cwd() / filestorage_location / filename for filename in self.fileNamesList]
        fileUrls = [QUrl().fromLocalFile(str(filepath)) for filepath in filePaths]
        print(fileUrls)
        mimeData.setUrls(fileUrls)
        mimeData.setData("app/fileList", QByteArray()) #make drag detectable so we can block it from being droppen back into the files window
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        #drag.exec_(Qt.MoveAction) for move instead of copy
        drag.exec_(Qt.CopyAction)
        print("Start drag")

nameForNewTag = "newTagName"

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
        self.itemChanged.connect(self.tagEditComplete)
        self.itemDelegate().closeEditor.connect(self.editClosed)
        #connect(self, SIGNAL(customContextMenuRequested(QPoint)), SLOT(customMenuRequested(QPoint)));)
    
    def editClosed(self):
        #deactivate editing after edit mode is closed
        self.lastItemInEditMode.setFlags(self.lastItemInEditMode.flags() & (~Qt.ItemIsEditable))
    
    def tagEditComplete(self, item):
        if(self.state() == QAbstractItemView.EditingState):
            newTagName = item.text(0)
            oldTagName = self.lastEditedTagname
            if(oldTagName == nameForNewTag):
                print(f"creating {newTagName} under {self.parentTagNameForNewTag}")
                sqlite3Backend.newTag(newTagName, self.parentTagNameForNewTag)
            else:
                print(f"renaming {oldTagName} to {newTagName}")
                sqlite3Backend.renameTag(oldTagName, newTagName)
                for tagsForFile in self.mainClassReference.filesTagsDict.values():
                    print(tagsForFile)
                    for tagIdx, tagName in enumerate(tagsForFile):
                        if tagName == oldTagName:
                            tagsForFile[tagIdx] = newTagName
                print(self.mainClassReference.filesTagsDict)
                self.mainClassReference.fileTable.on_selectionChanged(None, None)
        else:
            self.lastEditedTagname = item.text(0)

   
    
    def contextMenuEvent(self, event):
        if not self.currentItem():
            return
        currentTagItem = self.currentItem()
        currentTagName = currentTagItem.text(0)
        self.lastEditedTagname = currentTagItem.text(0)
        print(f"context menu with {self.lastEditedTagname}")
        tagContextMenu = QMenu(self)
        addAction = tagContextMenu.addAction("add child tag")
        renameAction = tagContextMenu.addAction("rename")
        if currentTagName != sqlite3Backend.rootTagName:
            deleteAction = tagContextMenu.addAction("delete")
        action = tagContextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == addAction:
            self.parentTagNameForNewTag = currentTagItem.text(0)
            childInTreeWidget = QTreeWidgetItem()
            childInTreeWidget.setText(0, "newTagName")
            currentTagItem.addChild(childInTreeWidget)
            childInTreeWidget.setFlags(childInTreeWidget.flags() | Qt.ItemIsEditable)
            currentTagItem.setExpanded(True)
            self.lastItemInEditMode = childInTreeWidget
            self.editItem(childInTreeWidget, 0)
            #the actual creation is done when the edit is confirmed / aborted in tagEditComplete
        elif action == renameAction:
            self.lastItemInEditMode = currentTagItem
            currentTagItem.setFlags(currentTagItem.flags() | Qt.ItemIsEditable)
            self.editItem(currentTagItem)
        elif currentTagName != sqlite3Backend.rootTagName and action == deleteAction:
            
            deletionConfirmed = DatengrabTagDeleteDialog(currentTagName).exec_()
            if deletionConfirmed:
                allDeletedTagNamesList = sqlite3Backend.deleteTagsAndChildTags(currentTagName)
                print(allDeletedTagNamesList)
                for deletedTagName in allDeletedTagNamesList:
                    for tagNames in self.mainClassReference.filesTagsDict.values():
                        if(deletedTagName in tagNames):
                            tagNames.remove(deletedTagName)
                self.mainClassReference.fileTable.on_selectionChanged(None, None)          
                currentTagItem.parent().removeChild(currentTagItem)
                self.removeItemWidget(currentTagItem, 0)

    def getDataFromBackend(self):
        self.clear()
        tagHierarchy = datengrabSql.getTagHierarchy()
        topLevelItem = self.recursiveTreeWidgetFill(tagHierarchy)
        self.addTopLevelItem(topLevelItem)
        topLevelItem.setExpanded(True)

    def recursiveTreeWidgetFill(self, currentTagInHierarchy):
        newChild = QTreeWidgetItem()
        newChild.setText(0, currentTagInHierarchy.name)
        for subTag in sorted(currentTagInHierarchy.childs, key=lambda x: x.name):
            newChild.addChild(self.recursiveTreeWidgetFill(subTag))
        return newChild

    def dropEvent(self, event):
        droppedOnQIndex = self.indexAt(event.pos())
        if(not droppedOnQIndex):
            event.ignore()
            return
        droppedOnTag = self.itemFromIndex(droppedOnQIndex)
        if(droppedOnTag is None):
            event.ignore()
            return 
        droppedOnTagName = droppedOnTag.text(0)
        print(f"dropped on {droppedOnTagName}")
        mimeData = event.mimeData()
        #check that mime data is a tag and that the drop target is a valid tag is on an valid element inside the tree view
        if(mimeData.hasFormat("app/tagName") and droppedOnTagName):
            draggedTag = self.storedDragItem
            draggedTagsParent = self.storedDragItem.parent()
            draggedTagName = draggedTag.text(0)
            if (draggedTagsParent == None) or (draggedTagsParent == droppedOnTag):
                event.ignore()
                return
            #make sure one can't tag one tree onto one of it's deeper nested childs or itself
            currentCheckedTagInHierarchy = droppedOnQIndex
            while(currentCheckedTagInHierarchy.data() != None):
                if(currentCheckedTagInHierarchy.data() == draggedTagName):
                    event.ignore()
                    return
                currentCheckedTagInHierarchy = currentCheckedTagInHierarchy.parent()
            sqlite3Backend.moveExistingTagToNewParent(draggedTagName, droppedOnTagName)
            indexOfChild = draggedTagsParent.indexOfChild(draggedTag)
            droppedOnTag.addChild(draggedTagsParent.takeChild(indexOfChild))
            droppedOnTag.setExpanded(True)
            event.accept()
            return
        event.ignore()


    def dragEnterEvent(self, event):
        if(event.mimeData().hasFormat("app/tagName")):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        droppedOnQIndex = self.indexAt(event.pos())
        if(not droppedOnQIndex):
            event.ignore()
            return
        droppedOnTag = self.itemFromIndex(droppedOnQIndex)
        if(droppedOnTag is None):
            print("Here")
            event.ignore()
            return 
        droppedOnTagName = droppedOnTag.text(0)
        #print(f"moved over {droppedOnTagName}")
        mimeData = event.mimeData()
        #check that mime data is a tag and that the drop target is a valid tag is on an valid element inside the tree view
        if(mimeData.hasFormat("app/tagName") and droppedOnTagName):
            draggedTag = self.storedDragItem
            draggedTagsParent = self.storedDragItem.parent()
            draggedTagName = draggedTag.text(0)
            if (draggedTagsParent == None) or (draggedTagsParent == droppedOnTag):
                event.ignore()
                return
            #make sure one can't tag one tree onto one of it's deeper nested childs or itself
            currentCheckedTagInHierarchy = droppedOnQIndex
            while(currentCheckedTagInHierarchy.data() != None):
                if(currentCheckedTagInHierarchy.data() == draggedTagName):
                    event.ignore()
                    return
                currentCheckedTagInHierarchy = currentCheckedTagInHierarchy.parent()
            event.accept()
            return
        event.ignore()
        return

    def startDrag(self, *args, **kwargs):
        mimeData = QMimeData()
        mimePayloadTagName = QByteArray(bytes(self.currentItem().text(0), encoding='utf8'))
        mimeData.setData("app/tagName", mimePayloadTagName)
        self.storedDragItem = self.currentItem()
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(Qt.MoveAction)
        print("tag drag")

class DatengrabSelectionTagsTable(QTableWidget):

    tableColumnNames = ["tagname", "num of selectecd files with this tag"]

    def __init__(self, mainClassReference):
        super().__init__()
        self.setColumnCount(2)
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
                if(self.mainClassReference.filesTagsDict):
                    self.mainClassReference.filesTagsDict[fileName] = sqlite3Backend.getTagsOfFile(fileName) #update tags of file
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
    
    def contextMenuEvent(self, event):
        if not self.currentItem():
            return
        currentTagItem = self.item(self.currentItem().row(), 0) 
        currentTagName = currentTagItem.text()
        tagContextMenu = QMenu(self)
        addToSelAction = tagContextMenu.addAction("add to all selected files")
        remFromSelAction = tagContextMenu.addAction("remove from all selected files")
        action = tagContextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == addToSelAction:
            for fileName in self.mainClassReference.fileTable.getSelectedFilesList():
                sqlite3Backend.addTagToFile(fileName, currentTagName)
                if(currentTagName not in self.mainClassReference.filesTagsDict[fileName]):
                    self.mainClassReference.filesTagsDict[fileName].append(currentTagName)
            self.mainClassReference.fileTable.on_selectionChanged(None, None)
        elif action == remFromSelAction:
            for fileName in self.mainClassReference.fileTable.getSelectedFilesList():
                sqlite3Backend.removeTagFromFile(fileName, currentTagName)
                if(currentTagName in self.mainClassReference.filesTagsDict[fileName]):
                    self.mainClassReference.filesTagsDict[fileName].remove(currentTagName)
            self.mainClassReference.fileTable.on_selectionChanged(None, None)
    

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
        fileSearchVBox_LineEdit.setPlaceholderText("datetime.fromtimestamp(fileStat.st_mtime) < datetime.now()")
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
            potentialFilesForTagSearchList = datengrabSql.getFilesWithTags(tagSearchString)
        except ValueError:
            lineEditErrorPalette = QPalette()
            lineEditErrorPalette.setColor(QPalette.Base, Qt.red)
            self.tagSearchLineEdit.setPalette(lineEditErrorPalette)
            self.progressBarAnimateStop()
            return
        
        def fileSearchFilter(fileName):
            
            importString = "exec('from datetime import datetime') or "
            importString += "exec('from os import path') or "
            localsDict = dict()
            
            localsDict["fileStat"] = os.stat(Path.cwd() / sqlite3Backend.filestorage_location / fileName)
            print(localsDict["fileStat"]) 
            return eval(importString + fileSearchString, None, localsDict)
        #todo handle file search (name, date, ...)
        if(fileSearchString):
            filteredFiles = list(filter(fileSearchFilter, potentialFilesForTagSearchList))
        else:
            filteredFiles = potentialFilesForTagSearchList
        #filteredFiles = potentialFilesForTagSearchList

        print(filteredFiles)
        
        self.filesList = filteredFiles
        self.filesTagsDict = dict()
        for filename in self.filesList:
            self.filesTagsDict[filename] = sqlite3Backend.getTagsOfFile(filename)


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
