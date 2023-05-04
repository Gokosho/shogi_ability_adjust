import re
import collections
import sys
import argparse
import glob
import pickle

###########最初に設定しておくもの##################################
trans1 = ['１', '２', '３', '４', '５', '６', '７', '８', '９']
trans2 = ['一', '二', '三', '四', '五', '六', '七', '八', '九']

koma_moji = ['飛', '角', '金', '銀', '桂', '香', '歩']
koma_kigo = ['r', 'b', 'g', 's', 'n', 'l', 'p']

koma_kigo2 = [x.swapcase() for x in koma_kigo] + koma_kigo

def make_sfen(retu):    
    for i in range(9, 0, -1):
        retu = retu.replace('0'*i, str(i))
    return retu

sfen_dan = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
#################################################################

# kif形式のファイルを読み込んで、その棋譜ファイルの各局面からなるsfenの指し手と局面図のペアのリストを返す
# 具体的には[(sfen指し手, sfen局面),...]
def make_sfen_from_file(file_path):
    with open(file_path, 'r') as f:
        kifu = f.read()

    # Blunder.Converterで将棋クエストの棋譜をkifに変換したものだと指し手以前にある文字列の影響でエラーが出ることがあるため
    # 「先手：」の行が1行目になるように一部を削除する
    target = '先手：'
    index = kifu.find(target)
    kifu = kifu[index:]

    for x in range(9):
        kifu = kifu.replace(trans1[x], str(x+1))
        kifu = kifu.replace(trans2[x], str(x+1))

    kifu = kifu.replace('\u3000', '')

    sashite = [x.groups()[0] 
        for x in re.finditer('^\s*[0-9]+\s+(\S+).*$', 
        kifu, 
        flags=re.MULTILINE)]

    for x in range(1, len(sashite)):
        if ('同' in sashite[x]):
            sashite[x] = sashite[x].replace('同', sashite[x-1][:2])

    if ('投了' in sashite):
        sashite.remove('投了')

    #SFENリスト
    sfen = []

    #持ち駒
    mochigoma = []

    # sfenの指し手リスト
    sfen_moves = []

    #局面データをlistに変換
    kyokumen = 'lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL'
    sfen.append(kyokumen + ' ' + 'b' + ' ' + '-' + ' ' + '1')
    for i in range(1, 10):
        kyokumen = kyokumen.replace(str(i), '0'*i)
    kyokumen = [list(x) for x in kyokumen.split('/')]

    #駒を動かす
    for i, each_sashite in enumerate(sashite):

        if each_sashite[-1] != '打': #駒を動かすときの処理
            
            move = re.match('^(\d+)(\D+)\((\d+).*$', each_sashite).groups()

            after_x = 9 - int(move[0][0])
            after_y = int(move[0][1]) - 1 

            before_x = 9 - int(move[2][0])
            before_y = int(move[2][1]) - 1

            active_koma = kyokumen[before_y][before_x]
            
            #移動元は空きになる
            kyokumen[before_y][before_x] = '0'

            #「成」ならば「+」をつける
            if move[1][-1] == '成':
                active_koma = '+' + active_koma

            #移動先に駒があれば持ち駒とする
            #大文字、小文字は入れ替える必要がある
            if kyokumen[after_y][after_x] != '0':
                mochigoma.append(kyokumen[after_y][after_x][-1].swapcase())
            
            #移動先に駒をセットする
            kyokumen[after_y][after_x] = active_koma

            # sfenの指し手を作る
            sfen_move = f'{move[2][0]}{sfen_dan[int(move[2][1]) - 1]}{move[0][0]}{sfen_dan[int(move[0][1]) - 1]}'
            if move[1][-1] == '成':
                sfen_move += '+'
            sfen_moves.append(sfen_move)

        else: #駒を打つときの処理

            after_x = 9 - int(each_sashite[0])
            after_y = int(each_sashite[1]) -1

            active_koma = koma_kigo[koma_moji.index(each_sashite[2])]

            if i % 2 == 0: #先手が駒を打つ
                active_koma = active_koma.upper()

            kyokumen[after_y][after_x] = active_koma

            mochigoma.remove(active_koma)

            # sfenの指し手を作る
            sfen_move = f'{str.upper(koma_kigo[koma_moji.index(each_sashite[2])])}*{each_sashite[0]}{sfen_dan[int(each_sashite[1]) - 1]}'
            sfen_moves.append(sfen_move)

        #SFENリストに保存    
        mochigoma_dict = collections.Counter(''.join(mochigoma))

        sfen_mochigoma = ''
        for x in koma_kigo2:
            if mochigoma_dict[x] == 1:
                sfen_mochigoma += x
            elif mochigoma_dict[x] > 1:
                sfen_mochigoma += (str(mochigoma_dict[x]) + x)
        
        if sfen_mochigoma =='':
            sfen_mochigoma = '-'

        sfen.append('/'.join([make_sfen(''.join(x)) for x in kyokumen]) 
                + ' ' + ('w' if i % 2 == 0 else 'b')
                + ' ' + sfen_mochigoma 
                + ' ' + str(i + 2))

    output_list = []
    for move, board in zip(sfen_moves, sfen):
        output_list.append((move, board))
    
    return output_list

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_folder')
    parser.add_argument('output_pkl')
    parser.add_argument('num', type=int)
    args = parser.parse_args()

    kifu_list = glob.glob(args.input_folder + '/*.kif')

    output_kifu_list = []
    for index, kifu in enumerate(kifu_list):
        if index >= args.num:
            break
        output_kifu_list.append(make_sfen_from_file(kifu))

    with open(args.output_pkl, 'wb') as f:
        pickle.dump(output_kifu_list, f)
