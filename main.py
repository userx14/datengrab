import sqlite3
import re
import datetime

sqlDB = sqlite3.connect('./datengrab.db')
sqlCursor = sqlDB.cursor()

sqlTablesInit = {
    'files':          '(FileId INT NOT NULL AUTO_INCREMENT,      FileName TEXT NOT NULL,                                    PRIMARY KEY(FileId))',
    'tags':            '(TagId INT NOT NULL AUTO_INCREMENT,       TagName TEXT NOT NULL, TagCreationDate DATETIME NOT NULL, PRIMARY KEY(TagId))',
    'refs':            '(RefId INT NOT NULL AUTO_INCREMENT,       TagIdRef INT NOT NULL,            FileIdRef INT NOT NULL, PRIMARY KEY(RefId))',
    'hierarchy': '(HierarchyId INT NOT NULL AUTO_INCREMENT, ParentTagIdRef INT NOT NULL,        ChildTagIdRef INT NOT NULL, PRIMARY KEY(HierarchyId))'
}

def checkIfTableExists(tablename):
    sqlCursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tablename}'")
    result = sqlCursor.fetchall()
    if(result):
        return True 
    else:
        return False

def firstTimeInit():
    #check if all tables exist
    for (tableName,tableFields) in allTableNames:
        if(not checkIfTableExists(tableName):
           print(f"Table {tableName} does not exist yet, adding to database...")
           sqlCursor.execute(f"CREATE TABLE {tableName} {tableFields}")

def checkLegalFileName(fileName):
    if re.match("[^A-Za-z._]", fileName):
        print("filename format not supported")
        exit()

def newFile(fileName):
    sqlCursor.execute(f"INSERT INTO files (FileName) VALUES (?)",(fileName)))

def newTag(tagName):
    taggingTime = datetime.now()
    sqlCursor.execute(f"INSERT INTO tags (TagName, TagCreationDate) VALUES (?,?)", (tagName, taggingTime))
    
def addTagToFile(fileName, tagName):
    sqlCursor.execute(f"SELECT FileId FROM files WHERE FileName='{fileName}'")
    fileId = sqlCursor.fetchone()
    if(not fileId):
        raise Exception("Database Corrupted")
    
    tagId = sqlCursor.execute(f"SELECT FileId FROM tags WHERE TagName='{tagName}'")
    if(not tagId):
        raise Exception("Database Corrupted")
    
    sqlCursor.execute()
    
def findTagsOfFile(filename):
    sqlCursor.execute(f"SELECT * FROM files WHERE FileName='{filename}' ")
def findFileWithTags(LogicalTagStatement):


firstTimeInit()
sqlDB.commit()