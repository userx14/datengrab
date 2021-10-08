import sqlite3
import re
import argparse
from sympy.parsing.sympy_parser import parse_expr
from sympy.logic import boolalg
from sympy.core import symbol
from datetime import datetime
from fileinput import filename

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
    
        
def renameTag(oldTagName, newTagName):
    sqlCursor.execute(f"""UPDATE tags
                          SET TagName = "{newTagName}"
                          WHERE TagName = "{oldTagName}";""")


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
    
    
    return [tagName[0] for tagName in sqlCursor.fetchall()]


def _getRefIdFromTagName(tagName):
    sqlCursor.execute(f"""SELECT TagId
                          FROM tags
                          WHERE TagName = "{tagName}"   
                          """)
    return sqlCursor.fetchone()[0]


def _sqlSubQueryFileIdWithoutTag(TagRefId, SubQueryName):
    subQueryAllFileIdWithoutTag =  f""" ( 
                                            SELECT refs.FileIdRef
                                            FROM refs
                                            LEFT OUTER JOIN (
                                                SELECT FileIdRef
                                                FROM refs
                                                WHERE refs.TagIdRef ="{TagRefId}"
                                            ) AS refsRemove
                                            ON refs.FileIdRef = refsRemove.FileIdRef
                                            WHERE refsRemove.FileIdRef IS NULL
                                            GROUP BY refs.FileIdRef 
                                        ) AS {SubQueryName} """
    return subQueryAllFileIdWithoutTag


def _sqlSubQueryFileIdWithTag(TagRefId, SubQueryName):
    subQueryAllFileIdWithTag =  f"""(
                                        SELECT refs.FileIdRef
                                        FROM refs
                                        WHERE refs.TagIdRef = "{TagRefId}"
                                        GROUP BY refs.FileIdRef
                                    ) AS {SubQueryName} """
    return subQueryAllFileIdWithTag


def _sqlSubQueryFromDnfAnd(dnfExpr, SubQueryName):
    #place first subquerry as first table
    SymbolOrNotOperator = dnfExpr.args[0]
    sqlQuery = " ( SELECT andSubQuery0.fileIdRef FROM "
    if(type(SymbolOrNotOperator) == boolalg.Not):
        tagRefId = _getRefIdFromTagName(SymbolOrNotOperator.args[0])
        sqlQuery += _sqlSubQueryFileIdWithoutTag(tagRefId, "andSubQuery0")
    else: #is ordinary symbol / tag
        tagRefId = _getRefIdFromTagName(SymbolOrNotOperator)
        sqlQuery += _sqlSubQueryFileIdWithTag(tagRefId, "andSubQuery0")
    
    #inner join all following arguments
    for argIdx in range(1, len(dnfExpr.args)):
        SymbolOrNotOperator = dnfExpr.args[argIdx]
        if(type(SymbolOrNotOperator) == boolalg.Not):
            tagRefId = _getRefIdFromTagName(SymbolOrNotOperator.args[0])
            sqlQuery += " INNER JOIN " 
            sqlQuery += _sqlSubQueryFileIdWithoutTag(tagRefId, f"andSubQuery{argIdx}")
            sqlQuery += f" ON andSubQuery0.fileIdRef = andSubQuery{argIdx}.fileIdRef "
        else:
            tagRefId = _getRefIdFromTagName(SymbolOrNotOperator)
            sqlQuery += " INNER JOIN "
            sqlQuery += _sqlSubQueryFileIdWithTag(tagRefId, f"andSubQuery{argIdx}")
            sqlQuery += f" ON andSubQuery0.fileIdRef = andSubQuery{argIdx}.fileIdRef "
    sqlQuery += f" ) AS {SubQueryName} "
    return sqlQuery        
    
    
def _sqlSubQueryFromDnfOr(dnfExpr, SubQueryName):
    #place first subquerry as first table
    SymbolOrAndOrNotOperator = dnfExpr.args[0]
    sqlQuery = " ( SELECT orSubQuery0.fileIdRef FROM "
    if(type(SymbolOrAndOrNotOperator) == boolalg.Not):
        tagRefId = _getRefIdFromTagName(SymbolOrAndOrNotOperator.args[0])
        sqlQuery += _sqlSubQueryFileIdWithoutTag(tagRefId, "orSubQuery0")
    elif(type(SymbolOrAndOrNotOperator) == boolalg.And):
        sqlQuery += _sqlSubQueryFromDnfAnd(SymbolOrAndOrNotOperator, "orSubQuery0")    
    else: #is ordinary symbol / tag
        tagRefId = _getRefIdFromTagName(SymbolOrAndOrNotOperator)
        sqlQuery += _sqlSubQueryFileIdWithTag(tagRefId, "orSubQuery0")
        
    #outer join all following arguments
    for argIdx in range(1, len(dnfExpr.args)):
        SymbolOrAndOrNotOperator = dnfExpr.args[argIdx]
        if(type(SymbolOrAndOrNotOperator) == boolalg.Not):
            tagRefId = _getRefIdFromTagName(SymbolOrAndOrNotOperator.args[0])
            sqlQuery += f" UNION SELECT orSubQuery{argIdx}.fileIdRef FROM "
            sqlQuery += _sqlSubQueryFileIdWithoutTag(tagRefId, f"orSubQuery{argIdx}")
        elif(type(SymbolOrAndOrNotOperator) == boolalg.And):
            sqlQuery += f" UNION SELECT orSubQuery{argIdx}.fileIdRef FROM "
            sqlQuery += _sqlSubQueryFromDnfAnd(SymbolOrAndOrNotOperator, f"orSubQuery{argIdx}")
        else:
            tagRefId = _getRefIdFromTagName(SymbolOrAndOrNotOperator)
            sqlQuery += f" UNION SELECT orSubQuery{argIdx}.fileIdRef FROM "
            sqlQuery += _sqlSubQueryFileIdWithTag(tagRefId, f"orSubQuery{argIdx}")
    sqlQuery += f" ) AS {SubQueryName} "
    return sqlQuery    
    
    
def findFilesWithTags(LogicalTagStatement):
    #TODO check for bad input which is a valid sympy expression
    
    #convert "not"-operator into readable format for sympy
    LogicalTagStatement = LogicalTagStatement.replace("!","~")
    
    #support implied AND   
    TagSplitted = re.split(r'([\w]+)', LogicalTagStatement)
    for tagIdx in range(len(TagSplitted)):
        #check if the current token is a tag
        if TagSplitted[tagIdx].isspace():
            TagSplitted[tagIdx] = " & "
        if TagSplitted[tagIdx].strip() == "~":
            TagSplitted[tagIdx] = " &~ "
        
    
    ExpressionString = ''.join(TagSplitted)
    print(f"expr: {ExpressionString}")
    
    dnfExpr = boolalg.to_dnf(parse_expr(ExpressionString))
    
    #if(type(dnfExpr) is boolalg.Not): TODO case for only one tag non negated
    sqlQuery = """SELECT files.FileName
                           FROM files
                           INNER JOIN"""
    selectedFileRefIds = None
    if(type(dnfExpr) == symbol.Symbol):
        #only search for a single tag
        TagRefId = _getRefIdFromTagName(dnfExpr)
        sqlQuery += _sqlSubQueryFileIdWithTag(TagRefId, "combinedFileRefSubQuery")
    elif(type(dnfExpr) == boolalg.Not):
        #only search for a single negated tag
        tagName = dnfExpr.args[0]
        currentTagRefId = _getRefIdFromTagName(tagName)
        sqlQuery += _sqlSubQueryFileIdWithoutTag(currentTagRefId, "combinedFileRefSubQuery")
    elif(type(dnfExpr) == boolalg.And):
        #search nested "and" with can have "not" or "symbols" as childs
        sqlQuery += _sqlSubQueryFromDnfAnd(dnfExpr, "combinedFileRefSubQuery")
    elif(type(dnfExpr) == boolalg.Or):       
        sqlQuery += _sqlSubQueryFromDnfOr(dnfExpr, "combinedFileRefSubQuery") 
        pass
    else:
        raise Exception("bad search string")
    sqlQuery += """ON files.FileId = combinedFileRefSubQuery.FileIdRef"""
    print(sqlQuery)
    sqlCursor.execute(sqlQuery)
    return [filename[0] for filename in sqlCursor.fetchall()]



"""
parser = argparse.ArgumentParser(description="tag based file manager")
parser.add_argument('-a', help="adds the following tags to...")
parser.add_argument('-c', help="...the specified filepaths which will be copied inside the tagging directory")
parser.add_argument('-d', help="removes the following tags from...")
parser.add_argument('-f', help="...the specified file names inside the tagging directory")
parser.add_argument('-s', help="search for the logically evaluated expressions of tags (supporting !,&,| and ->* for all children) (either by tagname or full hierarchical name ->software->pythonprogs or with wildcard ->computer->*)")
parser.add_argument('-i', help="database integrity check")
parser.add_argument('-u', help="disk usage stats and number of tracked files")
args = parser.parse_args()

"""



firstTimeInit()
newFile("testFile.txt")
newFile("testFile2.txt")
newFile("testFile3.txt")
newTag("tagA")
newTag("tagB")
newTag("tagC")
newTag("tagD")
addTagToFile("testFile.txt","tagA")
addTagToFile("testFile.txt","tagB")
addTagToFile("testFile2.txt","tagA")
addTagToFile("testFile2.txt","tagC")
addTagToFile("testFile2.txt","tagD")
addTagToFile("testFile3.txt","tagB")
addTagToFile("testFile3.txt","tagC")
findTagsOfFile("testFile.txt")
findTagsOfFile("testFile2.txt")
#findFileWithTags("tagC")
#findFileWithTags("tagA  tagB")
print(findFilesWithTags("tagA | tagD"))

sqlDB.commit()