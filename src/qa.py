import os
import sys
import codecs
import jieba
import numpy as np
import math
import pymysql
import platform
import time
import json

NEW_LINE = '\n'
if platform.system() == 'Windows':
    NEW_LINE = '\r\n'
WORD_BANK_FILE_PAYH = '../data/WordBank.txt'
VECTORS_FILE_PAYH = '../data/vectors.txt'

user = 'root'
password = 'keyan123'
dbName = 'railwayquestion'
tableName = 'question'


def calLen(vec):
    vec = np.mat(vec)
    num = (float)(vec * vec.T)
    return math.sqrt(num)

def norm(vec):
    vec = np.mat(vec)
    return vec / calLen(vec)

def cosSim(v1, v2):
    v1 = np.mat(v1)
    v2 = np.mat(v2)
    num = (float)(v1 * v2.T)
    return num

def toSet(mlist):
    temp = set()
    for elem in mlist:
        temp.add(elem)
    return temp

# 加载词库
def loadWordBank(filePath):
    fr = codecs.open(filePath, 'r', encoding='utf-8')
    content = fr.read()
    fr.close()
    wordBank = content.split(NEW_LINE)
    wordBank.remove( wordBank[-1] )
    return wordBank

# 找答案
def answer(question):
    # print('\tstart...')
    t1 = time.time()
    # 分词
    question = jieba.lcut(question) # 分词
    # print('\t[jieba]', time.time() - t1)
    # t1 = time.time()
    i = 0
    # 把每个词都替换成对应的id，词库中没有则抛弃
    while i < len(question):
        if question[i] in wordBank:
            # 把每个词都替换成对应的id
            question[i] = wordBank.index( question[i] )
            i += 1
        else:
            # # 词库中没有该词，抛弃
            # question.remove( question[i] )
            process = proc(question[i])
            print('\t[process]', process)
            if len(process) > 0:
                question[i] = wordBank.index( process[0] )
                i += 1
            else:
                question.remove( question[i] )
    # 将问题文本表示为向量
    # print('\t[procWords]', time.time() - t1)
    # t1 = time.time()
    words = list(toSet(question))
    words.sort()
    # print('\t[wordSorted]', time.time() - t1)
    # t1 = time.time()
    vector = [0 for ii in range(0, len(wordBank))]
    for word in words:
        vector[word] = question.count(word)
    if calLen(vector) > 0:
        vector = norm(vector) # 新问题的向量
    # print('\t[word2vec]', time.time() - t1)
    # t1 = time.time()
    # 计算余弦相似度
    sims = []
    for doc in vectors:
        vec = doc[1]
        sim = cosSim(vector, vec) # 计算余弦相似度
        sims.append(sim)
        # if sim > maxSim:
        #     maxSim = sim # 更新最近问题的余弦距离
        #     indexOfSim = doc[0] # 最近问题的id（此处变量类型为字符串，便于组织sql语句）
    indexs = []
    ansCnt = len(sims) - sims.count(0)
    # 非零的相似度距离分数 按 三个以上 和 以下 分类处理
    if ansCnt > 2:
        ansCnt = 3
    for i in range(0, ansCnt):
        maxIdx = sims.index( max(sims) ) # 当前最大值的索引
        sims[maxIdx] = 0 # 当前最大值归零，相当于删除该值
        indexs.append(maxIdx + 1) # 记录当前最大值的索引值 + 1，加1 是因为数据库中的id比这里的索引值大1
    # print('\t[getIndexs]', time.time() - t1)
    # t1 = time.time()
    print('MaxSimIndexs', indexs)
    if len(indexs) > 0:
        answers = getAnswers(indexs)
        for i in range(0, len(answers)):
            ans = answers[i]
            ansJson = dict()
            ansJson['question'] = str(ans[0]).strip()
            ansJson['answer'] = str(ans[1]).strip()
            answers[i] = ansJson
        ansJson = json.dumps(answers, ensure_ascii=False)
        return ansJson
    else:
        return str(json.dumps([])) # 没有找到答案，返回空

# 从数据库中获取 特定id 的答案
def getAnswers(indexs):
    # t1 = time.time()
    db = pymysql.connect("localhost", user, password, dbName, charset='utf8') # 连接数据库
    cursor = db.cursor() # 建立游标
    answers = []
    sql = "select question, answer from question where id=%d;"
    for index in indexs:
        # cursor.execute(sql + str(index) + ';') # 执行查询
        cursor.execute(sql % index) # 执行查询
        ans = cursor.fetchone()
        answers.append(ans)
    cursor.close() # 关闭连接
    db.close()
    # print('\t[getAnswers]', time.time() - t1)
    return answers

# 读取向量
# 参数 wordBankLen ，是词库的长度
def loadVector(wordBankLen):
    fr = codecs.open(VECTORS_FILE_PAYH, 'r', encoding='utf-8')
    content = fr.read() # 读文件
    fr.close()
    vectors = content.split(NEW_LINE) # 按行分割
    vectors.remove( vectors[-1] ) # 去掉末尾的空元素
    for i in range(0, len(vectors)):
        vectorInfo = vectors[i]
        vectorInfo = vectorInfo.split('|') # [id, 'index:value ...'] 具体结构参考 ../data/vectors.txt
        tempVector = [0 for i in range(0, wordBankLen)]
        parts = vectorInfo[1].split(' ')
        for part in parts:
            indexAndNum = part.split(':')
            tempVector[int(indexAndNum[0])] = float(indexAndNum[1]) # 整理向量各维度参数
        vectorInfo[1] = tempVector
        vectors[i] = vectorInfo # （覆盖）保存为 vectors 中的第 i 个元素
    return vectors
'''
# 读取向量
def loadVector(wordBankLen):
    db = pymysql.connect("localhost", user, password, dbName, charset='utf8') # 连接数据库
    cursor = db.cursor() # 建立游标
    sql = "select id, vector from question;"
    cursor.execute(sql) # 执行查询
    vectors = []
    for row in cursor.fetchall():
        vectorInfo = list()
        vectorInfo.append(str(row[0])) # id
        tempVector = [0 for i in range(0, wordBankLen)]
        parts = row[1].split(' ')
        for part in parts:
            indexAndNum = part.split(':')
            tempVector[int(indexAndNum[0])] = float(indexAndNum[1]) # 整理向量各维度参数
        vectorInfo.append(tempVector)
        vectors.append(vectorInfo)
    cursor.close()
    db.close()
    return vectors
'''

# 可能近义词处理
def proc(word):
    t1 = time.time()
    word = list(word)
    words = []
    flag = False
    for w in word:
        for ww in wordBank:
            if w in ww:
                words.append(ww)
                flag = True
                break
        if flag:
            break
    print('\t[procWord]', time.time() - t1)
    return words

# t1 = time.time()
wordBank = loadWordBank(WORD_BANK_FILE_PAYH) # 加载词库
# print('\t[word2vec]', time.time() - t1)
# t1 = time.time()
vectors = loadVector(len(wordBank)) # 加载已知问题的向量
# print('\t[word2vec]', time.time() - t1)
# t1 = time.time()

# 入口
if __name__ == '__main__':
    # 判断新问题
    question = input('Input: ')
    while question != 'EXIT':
        answers = answer(question)
        print('\nAnswer:')
        for ans in answers:
            print(ans)
        question = input('Input: ')