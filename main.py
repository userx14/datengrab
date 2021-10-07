import sqlite3
import re
from datetime import datetime

sqlDB = sqlite3.connect('./datengrab.db')
sqlCursor = sqlDB.cursor()

sqlTablesInit = {
    'files': 
    """(FileId INTEGER PRIMARY KEY, 
        FileName TEXT NOT NULL,
        UNIQUE(FileName))""",
     
    'tags': """(TagId INTEGER PRIMARY KEY,
                TagName TEXT NOT NULL,
                TagCreationDate DATETIME NOT NULL,
                UNIQUE(TagName))""",
                
    'refs': """(RefId INTEGER PRIMARY KEY,
                TagIdRef INTEGER NOT NULL,
                FileIdRef INTEGER NOT NULL,
                FOREIGN KEY(TagIdRef) REFERENCES tags(TagId),
                FOREIGN KEY(FileIdRef) REFERENCES files(FileId),
                UNIQUE(TagIdRef, FileIdRef))""",
                
    'hierarchy': """(HierarchyId INTEGER PRIMARY KEY,
                    ParentTagIdRef INTEGER NOT NULL,
                    ChildTagIdRef INTEGER NOT NULL,
                    FOREIGN KEY(ParentTagIdRef) REFERENCES tags(TagId),
                    FOREIGN KEY(ChildTagIdRef) REFERENCES tags(TagId),
                    UNIQUE(ParentTagIdRef, ChildTagIdRef))"""
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
    for (tableName,tableFields) in sqlTablesInit.items():
        if(not checkIfTableExists(tableName)):
            print(f"Table {tableName} does not exist yet, adding to database...")
            sqlCursor.execute(f"CREATE TABLE {tableName} {tableFields};")

def checkLegalFileName(fileName):
    if re.match("[^A-Za-z._]", fileName):
        print("filename format not supported")
        exit()

def newFile(fileName):
    sqlCursor.execute(f"SELECT FileId FROM files WHERE FileName='{fileName}';")
    fileId = sqlCursor.fetchone()
    if(fileId):
        print("file does already exist")
    else:
        sqlCursor.execute(f"INSERT INTO files (FileName) VALUES (?);", (fileName,))

def newTag(tagName):
    tagId = sqlCursor.execute(f"SELECT TagId FROM tags WHERE TagName='{tagName}';")
    fileId = sqlCursor.fetchone()
    if(fileId):
        print("tag does already exist")
    else:
        taggingTime = datetime.now()
        sqlCursor.execute(f"INSERT INTO tags (TagName, TagCreationDate) VALUES (?,?);", (tagName, taggingTime))
    
def addTagToFile(fileName, tagName):
    sqlCursor.execute(f"SELECT FileId FROM files WHERE FileName='{fileName}';")
    fileIdTulple = sqlCursor.fetchone()
    if(not fileIdTulple):
        raise Exception("Database Corrupted")
    
    sqlCursor.execute(f"SELECT TagId FROM tags WHERE TagName='{tagName}';")
    tagIdTulple = sqlCursor.fetchone()
    if(not tagIdTulple):
        raise Exception("Database Corrupted")
    
    #check if reference is already existing
    sqlCursor.execute(f"""SELECT EXISTS(
                          SELECT * 
                          FROM refs 
                          WHERE TagIdRef=?
                          AND FileIdRef=?);""", (tagIdTulple[0], fileIdTulple[0]))
    alreadyExists = sqlCursor.fetchone()[0]
    if not alreadyExists:
        sqlCursor.execute(f"INSERT INTO refs (TagIdRef, FileIdRef) VALUES (?,?);", (tagIdTulple[0], fileIdTulple[0]))
    else:
        print("ref already exists")
    
        
    
def findTagsOfFile(filename):
    
    #relates the files to the tags by performing a double join with the refs table
    #then only the tag name is extracted
    
    sqlCursor.execute(f"""SELECT taglist.TagName 
                          FROM 
                          (
                          SELECT * 
                          FROM files 
                          INNER JOIN refs ON refs.FileIdRef = files.FileId 
                          INNER JOIN tags On tags.TagId = refs.TagIdRef
                          WHERE FileName='{filename}' 
                          ) AS taglist;""")
    
    
    tagNames = sqlCursor.fetchall()
    print(tagNames)
    
def findFileWithTags(LogicalTagStatement):
    pass

firstTimeInit()
newFile("testFile.txt")
newFile("testFile2.txt")
newTag("tagA")
newTag("tagB")
newTag("tagC")
newTag("tagD")
addTagToFile("testFile.txt","tagA")
addTagToFile("testFile.txt","tagB")
addTagToFile("testFile2.txt","tagA")
addTagToFile("testFile2.txt","tagC")
addTagToFile("testFile2.txt","tagD")
findTagsOfFile("testFile.txt")
findTagsOfFile("testFile2.txt")

sqlDB.commit()