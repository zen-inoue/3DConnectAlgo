from typing import List, Tuple
from local_driver import Alg3D, Board # ローカル検証用
#from framework import Alg3D, Board # 本番用

class MyAI(Alg3D):
    def get_move(
        self,
        board: List[List[List[int]]], # 盤面情報
        player: int, # 先手(黒):1 後手(白):2
        last_move: Tuple[int, int, int] # 直前に置かれた場所(x, y, z)
    ) -> Tuple[int, int]:
        self.board = board
        self.myPlayer = player
        self.opponentPlayer = 1 if player == 2 else 2    

        # テスト用に石を配置するコード(デバッグ用) @TODO コメントアウト
        ##self.do_test_put()

        # 初期化
        self.do_initialize(board, player)

        # 即置き判断(いわゆるpr0:最優先事項。)
        # 必勝点があればおく。
        if(len(self.memoryST_winInstant_3Dpoints) > 0):
            z,y,x = self.memoryST_winInstant_3Dpoints[0]
            if(self.is_posible_to_place(z,y,x)):
                print(f"必勝点に配置します (z,y,x)=({z},{y},{x})")
                return (x,y)

        print("↓うまく機能してない↓")
        print(self.memoryST_loseInstant_3Dpoints)
        for z,y,x in self.memoryST_loseInstant_3Dpoints:
            print(f"{z},{y},{x}")
            if(z > 0):
                print(self.board[z-1][y][x])


        # 置かないと必負点となる場所に置く
        if(len(self.memoryST_loseInstant_3Dpoints) > 0):
            ## instantバグあり 暫定回避 @TODO
            for z,y,x in self.memoryST_loseInstant_3Dpoints:
                if(self.is_posible_to_place(z,y,x)):
                    print(f"必敗点を回避するために配置します (z,y,x)=({z},{y},{x})")
                    return (x,y)
        
        print("test1")
        # 置いたら負けるところにはおかない。但し、それが無ければ物理的におけるところに置くしかない。
        # 座標の若いところに置くと自動的に相手が置く可能性が高まることから座標の大きいところに優先的に置く。
        if(len(self.logical_pr1_possible_3Dpoints) == 0):
            print("論理的着手可能点Pr1がありません")
            z,y,x = self.place_max(self.memoryST_physical_possible_3Dpoints)
            print(f"物理的着手可能点に配置します (z,y,x)=({z},{y},{x})")
            return (x,y)
        
        print("ttt")
        # pr1 過去学習結果、勝利確定条件であればその手を打つ。(これは考慮が難しい為実装見送り)
        # pr1-1: z=0の解析結果を使用する。(比較的登場頻度が多いため)
        #        全通りは最大3^16通りありそこからの再起計算かんがえると現実的ではない。
        #        その為、[ リーチ→強制手→ダブルリーチ ]のみ解析する。
        #        →これも組合せ爆発が生じた為、この状況が起きやすい状況を2軸主体で計算する。
        #        →これも計算が複雑。保留 @TODO なんらか対応
        ## self.study_code_pr1_z0()
        
        # pr2 自分のダブルリーチ手があれば置く。
        if(len(self.memoryST_doubleReach_possible_3Dpoints) != 0):
            z,y,x = self.place_max(self.memoryST_doubleReach_possible_3Dpoints)
            
            return (x,y)
        # pr2 相手のダブルリーチを防ぐ
        if(len(self.memoryST_opponent_doubleReach_possible_3Dpoints) != 0):
            z,y,x = self.place_max(self.memoryST_opponent_doubleReach_possible_3Dpoints)
            return (x,y)

        # pr3 完全勝利確定がmemoryLTで判明している場合はおく。
        # z0の2個並んだ状況は危険。重要重みづけを行う。
        self.caluculate_importance_z0()


        

        # pr4 相手の着手禁止手が増えるところ。重みづけ。 @TODO 要実装
        # pr5 座標的重みづけで優位なところに置く
        self.caluculate_importance_by_address()
        # pr6 自分がリーチになるところには極力置かない(ダブルリーチ状況が減ることが予想されるため)


        print("aaa")
        print(self.cell_important_value_board)
        print("bbb")
        # 重みづけ最大のところに置く。
        z,y,x = self.get_most_important()
        print("test1")
        print(board[z][y][x])
        if(self.is_posible_to_place(z,y,x) == False):
            print(f"{z},{y},{x}はおけない。")
            ## なぜかおけない場合は、下記で配置。
            z,y,x = self.place_max(self.logical_pr1_possible_3Dpoints)
        return (x,y)

    
    ############### 座標ごとの優先度計算 ################
    
    def caluculate_importance_z0(self):
        self.cell_important_value_board = self.get_empty_board()
        check_target_rowDict : dict[int,int] ={}
        basekey_list : list[int] = []
        for idx in range(4):
            basekey_list.append(MyAI.IDX_check_target_rowListX * 10 + idx)
        for idx in range(4):
            basekey_list.append(MyAI.IDX_check_target_rowListY * 10 + idx)
        basekey_list.append(MyAI.IDX_check_target_rowListZDiagnal * 10 + 0) ##(z,y,x)=(0,0,0)からはじまる斜め
        basekey_list.append(MyAI.IDX_check_target_rowListZDiagnal * 10 + 3) ##(z,y,x)=(0,0,3)からはじまる斜め

        for basekey in basekey_list:
            tmp_cnt_myPlayer = 0
            tmp_cnt_opponent = 0
            tmp_cnt_empty = 0

            if(basekey // 10 == MyAI.IDX_check_target_rowListX):
                idx = basekey % 10
                for x in range(4):
                    stoneType = self.board[0][idx][x]
                    if stoneType == 0:
                        tmp_cnt_myPlayer = 0
                        tmp_cnt_opponent = 0
                        tmp_cnt_empty = 0
                        for idx_tmp in range(4):
                            stoneTypeTmp = self.board[0][idx][idx_tmp]
                            if stoneTypeTmp == self.myPlayer:
                                tmp_cnt_myPlayer = tmp_cnt_myPlayer + 1
                            elif stoneTypeTmp == self.opponentPlayer:
                                tmp_cnt_opponent = tmp_cnt_opponent + 1
                            else: ## 空
                                tmp_cnt_empty = tmp_cnt_empty + 1
                        if tmp_cnt_empty == 2 and tmp_cnt_myPlayer == 2:
                            self.cell_important_value_board[0][idx][x] += MyAI.IMP_Z0_2STONES_MYPLAYER
                        if tmp_cnt_empty == 2 and tmp_cnt_opponent == 2:
                            self.cell_important_value_board[0][idx][x] += MyAI.IMP_Z0_2STONES_OPPONENT

            if(basekey // 10 == MyAI.IDX_check_target_rowListY):
                idx = basekey % 10
                for y in range(4):
                    stoneType = self.board[0][y][idx]
                    if stoneType == 0:
                        tmp_cnt_myPlayer = 0
                        tmp_cnt_opponent = 0
                        tmp_cnt_empty = 0
                        for idx_tmp in range(4):
                            stoneTypeTmp = self.board[0][idx_tmp][idx]
                            if stoneTypeTmp == self.myPlayer:
                                tmp_cnt_myPlayer = tmp_cnt_myPlayer + 1
                            elif stoneTypeTmp == self.opponentPlayer:
                                tmp_cnt_opponent = tmp_cnt_opponent + 1
                            else: ## 空
                                tmp_cnt_empty = tmp_cnt_empty + 1
                        if tmp_cnt_empty == 2 and tmp_cnt_myPlayer == 2:
                            self.cell_important_value_board[0][y][idx] += MyAI.IMP_Z0_2STONES_MYPLAYER
                        if tmp_cnt_empty == 2 and tmp_cnt_opponent == 2:
                            self.cell_important_value_board[0][y][idx] += MyAI.IMP_Z0_2STONES_OPPONENT


            if(basekey // 10 == MyAI.IDX_check_target_rowListZDiagnal):
                idx = basekey % 10
                if(idx == 0):
                    for idx2 in range(4):
                        stoneType = self.board[0][idx2][idx2]
                        if stoneType == 0:
                            tmp_cnt_myPlayer = 0
                            tmp_cnt_opponent = 0
                            tmp_cnt_empty = 0
                            for idx_tmp in range(4):
                                stoneTypeTmp = self.board[0][idx_tmp][idx_tmp]
                                if stoneTypeTmp == self.myPlayer:
                                    tmp_cnt_myPlayer = tmp_cnt_myPlayer + 1
                                elif stoneTypeTmp == self.opponentPlayer:
                                    tmp_cnt_opponent = tmp_cnt_opponent + 1
                                else: ## 空
                                    tmp_cnt_empty = tmp_cnt_empty + 1
                            if tmp_cnt_empty == 2 and tmp_cnt_myPlayer == 2:
                                self.cell_important_value_board[0][idx2][idx2] += MyAI.IMP_Z0_2STONES_MYPLAYER
                            if tmp_cnt_empty == 2 and tmp_cnt_opponent == 2:
                                self.cell_important_value_board[0][idx2][idx2] += MyAI.IMP_Z0_2STONES_OPPONENT

                else: ##idx == 3
                    for idx2 in range(4):
                        stoneType = self.board[0][idx2][3 - idx2]
                        if stoneType == 0:
                            tmp_cnt_myPlayer = 0
                            tmp_cnt_opponent = 0
                            tmp_cnt_empty = 0
                            for idx_tmp in range(4):
                                stoneTypeTmp = self.board[0][idx_tmp][3 - idx_tmp]
                                if stoneTypeTmp == self.myPlayer:
                                    tmp_cnt_myPlayer = tmp_cnt_myPlayer + 1
                                elif stoneTypeTmp == self.opponentPlayer:
                                    tmp_cnt_opponent = tmp_cnt_opponent + 1
                                else: ## 空
                                    tmp_cnt_empty = tmp_cnt_empty + 1
                            if tmp_cnt_empty == 2 and tmp_cnt_myPlayer == 2:
                                self.cell_important_value_board[0][idx2][3 - idx2] += MyAI.IMP_Z0_2STONES_MYPLAYER
                            if tmp_cnt_empty == 2 and tmp_cnt_opponent == 2:
                                self.cell_important_value_board[0][idx2][3 - idx2] += MyAI.IMP_Z0_2STONES_OPPONENT

    def caluculate_importance_by_address(self):
        add_imp = 0
        if self.count_stone < 6:
            add_imp = MyAI.IMP_ENPOWER_FIRST
        self.cell_important_value_board[0][0][0] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[0][0][3] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[0][3][0] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[0][3][3] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[3][0][0] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[3][0][3] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[3][3][0] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[3][3][3] += MyAI.IMP_ADDRESS + add_imp

        self.cell_important_value_board[1][1][1] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[1][1][2] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[1][2][1] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[1][2][2] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[2][1][1] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[2][1][2] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[2][2][1] += MyAI.IMP_ADDRESS + add_imp
        self.cell_important_value_board[2][2][2] += MyAI.IMP_ADDRESS + add_imp
    
    def get_most_important(self) -> Tuple[int,int,int]:
        max_imp = 0
        max_z = 0
        max_y = 0
        max_x = 0
        for z in range(4):
            for y in range(4):
                for x in range(4):
                    if self.is_posible_to_place(z,y,x) and (z,y,x) in self.logical_pr1_possible_3Dpoints:
                        tmp_imp =self.cell_important_value_board[z][y][x]
                        if max_imp < tmp_imp:
                            max_imp = tmp_imp
                            max_z,max_y,max_x = z,y,x
        return max_z,max_y,max_x
        


    ############### 重要2軸計算 ################
    IDX_check_target_surfaceListXY : int = 10
    IDX_check_target_surfaceListYZ : int = 11
    IDX_check_target_surfaceListZX : int = 12
    ## Y軸、X軸の斜めは揃えずらいので考慮不要でよいと判断。
    IDX_check_target_surfaceListZDiagnal : int = 15
    def caluculate_importance(self):
        check_target_surfaceDict : dict[str,int]={}
        basekey_surface_list : list[int] = []
        base_key = 0
        cnt_0 = 0
        cnt_1 = 0
        cnt_2 = 0
        surface_cnt_dic: dict[int]= {}
        surface_cnt_dic[0] = 0
        surface_cnt_dic[1] = 0
        surface_cnt_dic[2] = 0
        for z in range(4):
            for y in range(4):
                for x in range(4):
                    ## z = 0 のとき
                    v = self.board[z][y][x]
                    surface_cnt_dic[v] += 1

        ## 面単位のチェックも
        basekey_for_check = self.get_basekey_for_check_surface(self.IDX_check_target_surfaceListXY, 0, 0, 0)
        basekey_surface_list.append(basekey_for_check)
        ## 面単位のチェックも
        basekey_for_check = self.get_basekey_for_check_surface(self.IDX_check_target_surfaceListXY, 1, 0, 0)
        basekey_surface_list.append(basekey_for_check)
        ## 面単位のチェックも
        basekey_for_check = self.get_basekey_for_check_surface(self.IDX_check_target_surfaceListXY, 2, 0, 0)
        basekey_surface_list.append(basekey_for_check)
        ## 面単位のチェックも
        basekey_for_check = self.get_basekey_for_check_surface(self.IDX_check_target_surfaceListXY, 3, 0, 0)
        basekey_surface_list.append(basekey_for_check)
                    
    def get_basekey_for_check_surface(self,idx_for_check_surface,i):
        return idx_for_check_surface * 100 + i * 10

    ############### 一括初期化処理 ################
    def do_initialize(self, board : List[List[List[int]]], player : int):
        self.stone_count = 0
        self.count_stone()
        self.cell_important_value_board = []
        self.memoryST_winInstant_3Dpoints = []
        self.memoryST_doubleReach_not_possible_3Dpoints = []
        self.memoryST_loseInstant_3Dpoints = []
        self.init_all_row_zyx_list()
        self.init_memoryST_physical_possible_3Dpoints()
        self.init_memoryST_winInstant_3Dpoints()  
        self.init_memoryST_doubleReach_3Dpoints()  
        # 知見を元に勝利状況とその座標を取得する。
        self.memoryLT_winning_3Dpoints = []
        self.memoryLT_losing_3Dpoints = []
        self.init_logical_pr1_possible_3Dpoints()
        return


    # 盤面の情報
    board : List[List[List[int]]]
    # 自分の手番
    myPlayer : int
    opponentPlayer : int
    stone_count = 0

    # 解析結果後の盤面情報
    # 0:無影響空値 1:自分,2:相手,3:自分即勝利空値,4:相手即勝利空値,5:相手置くことで次自分が勝てる,6:自分が置くことで次相手が勝てる
    ## analyzed_board : List[List[List[int]]] ## 未使用 @TODO
    cell_important_value_board : List[List[List[int]]]
    IMP_Z0_2STONES_MYPLAYER = 10
    IMP_Z0_2STONES_OPPONENT = 20
    IMP_ADDRESS = 5
    IMP_ENPOWER_FIRST = 20

    #物理的着手可能点(z,x,y)
    memoryST_physical_possible_3Dpoints : List[Tuple[int,int,int]] = []
    #短期メモリーによる3D座標での必勝点
    memoryST_winInstant_3Dpoints : List[Tuple[int,int,int]] = []
    #短期メモリーによる3D座標での必敗点 ※おかないとだめ
    #(その点が勝利点になる場合は勝ちを優先してよいが、ここのリストには含まれる)
    memoryST_loseInstant_3Dpoints : List[Tuple[int,int,int]] = []
    #ダブルリーチ点(即おけるもの)
    memoryST_doubleReach_possible_3Dpoints : List[Tuple[int,int,int]] = []
    #ダブルリーチ点(即おけないもの)
    memoryST_doubleReach_not_possible_3Dpoints : List[Tuple[int,int,int]] = []
    #相手ダブルリーチ点(即おけるもの)
    memoryST_opponent_doubleReach_possible_3Dpoints : List[Tuple[int,int,int]] = []
    #相手ダブルリーチ点(即おけないもの)
    memoryST_opponent_doubleReach_not_possible_3Dpoints : List[Tuple[int,int,int]] = []

    #必勝法長期メモリーを考慮した勝利点(場面全体考慮)
    memoryLT_winning_3Dpoints : List[Tuple[int,int,int]] = [] # @TODO 未実装
    #必勝法長期メモリーを考慮した敗北点(場面全体考慮)
    memoryLT_losing_3Dpoints : List[Tuple[int,int,int]] = [] # @TODO 未実装

    #論理的着手可能点pr1
    #その上(z+1)が相手の勝利着手点ではない。
    logical_pr1_possible_3Dpoints : List[Tuple[int,int,int]] = []

    # LT: Long Term (場面全体を考慮)

    ### ここからは厳密性は欠くが、戦略的に実効性の高いものを列挙しmemoryLTに記憶する。
    # 1.平面における勝利メモリー(z=1)
    # 2.立体直線における勝利メモリー(x=固定またはy=固定)
    #   但し、空間的な作用を考慮する必要がある。
    #   0=空,1=自分,2=相手,3=空だが即勝点。4=空だが即敗点。
    # 3.配置した全直線及びz+1が関わる全直線に関わるもの。
    def testtest():
        print("test")

    ############### 初期化関数群 ################
    def count_stone(self):
        cnt = 0
        for z in range(4):
            for y in range(4):
                for x in range(4):
                    if(self.board[z][y][x] != 0):
                        cnt = cnt+1
        self.count_stone = cnt

        


    def init_memoryST_physical_possible_3Dpoints(self):
        self.memoryST_physical_possible_3Dpoints = []
        # @TODO: 高速化：過去の確認結果を踏まえる
        # self.boardを走査して、物理的に置ける場所を探す。
        for z,y,x in [(z,y,x) for z in range(4) for y in range(4) for x in range(4)]:
            if(self.is_posible_to_place(z,y,x)):
                self.memoryST_physical_possible_3Dpoints.append((z,y,x))
    
    def get_basekey_for_check(self, idx_check_target_rowType , idx_targetKey_z, idx_targetKey_y, idx_targetKey_x) -> int:
        return idx_check_target_rowType*10000 + idx_targetKey_z*1000 + idx_targetKey_y*100 + idx_targetKey_x*10

    def get_key_for_check(self, idx_check_target_rowType , idx_targetKey_z, idx_targetKey_y, idx_targetKey_x , stoneType) -> int:
        return self.get_basekey_for_check(idx_check_target_rowType , idx_targetKey_z, idx_targetKey_y, idx_targetKey_x) + stoneType

    def get_key_for_check_multi(self, idx_check_target_rowType , idx_targetKey_z, idx_targetKey_y, idx_targetKey_x) -> Tuple[int, int]:
        basekey = self.get_basekey_for_check(idx_check_target_rowType , idx_targetKey_z, idx_targetKey_y, idx_targetKey_x)
        return  basekey + 0, basekey + 1, basekey + 2
    
    def check_and_add_for_check(self, check_target_rowDict : dict[str,int], key_for_check:str) ->  dict[str,int]:
        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
        check_target_rowDict[key_for_check] = cnt+1
        return check_target_rowDict
    
    def get_effective_row_zyx_list(self,z, y, x) -> List[List[Tuple[int,int,int]]]:
        effective_row_zyx_list : List[List[Tuple[int,int,int]]] = []
        # z方向
        effective_row_zyx_list.append([(i,y,x) for i in range(4)])
        # y方向
        effective_row_zyx_list.append([(z,i,x) for i in range(4)])
        # x方向
        effective_row_zyx_list.append([(z,y,i) for i in range(4)])
        # z固定した斜め
        if(y == x):
            effective_row_zyx_list.append([(z,i,i) for i in range(4)])
        if(y == 3 - x):
            effective_row_zyx_list.append([(z,i,3 - i) for i in range(4)])
        # y固定した斜め
        if(z == x):
            effective_row_zyx_list.append([(i,y,i) for i in range(4)])
        if(z == 3 - x):
            effective_row_zyx_list.append([(3 - i,y,i) for i in range(4)])
        # x固定した斜め
        if(z == y):
            effective_row_zyx_list.append([(i,i,x) for i in range(4)])
        if(z == 3 - y):
            effective_row_zyx_list.append([(3 - i,i,x) for i in range(4)])
        # 立体斜め
        if(x == y and y == z):
            effective_row_zyx_list.append([(i,i,i) for i in range(4)])
        if(x == y and y == 3 - z):
            effective_row_zyx_list.append([(3 - i,i,i) for i in range(4)])
        if(x == 3 - y and y == z):
            effective_row_zyx_list.append([(i,3 - i,i) for i in range(4)])
        if(x == 3 - y and y == 3 - z):
            effective_row_zyx_list.append([(3 - i,3 - i,i) for i in range(4)])
        return effective_row_zyx_list
    
    ALL_ROW_XYZ_List : List[List[Tuple[int,int,int]]] = []
    
    def init_all_row_zyx_list(self):
        all_row_zyx_list : List[List[Tuple[int,int,int]]] = []
        row_zyx_list :list = []
        for z in range(4):
            for y in range(4):
                row_zyx = []
                for x in range(4):
                    row_zyx.append((z,y,x))
                all_row_zyx_list.append(row_zyx)
        for z in range(4):
            for x in range(4):
                row_zyx = []
                for y in range(4):
                    row_zyx.append((z,y,x))
                all_row_zyx_list.append(row_zyx)
        for y in range(4):
            for x in range(4):
                row_zyx = []
                for z in range(4):
                    row_zyx.append((z,y,x))
                all_row_zyx_list.append(row_zyx)
        # 斜め方向
        for z in range(4):
            row_zyx = []
            for i in range(4):
                row_zyx.append((z,i,i))
            all_row_zyx_list.append(row_zyx)
            row_zyx = []
            for i in range(4):
                row_zyx.append((z,i,3 - i))
            all_row_zyx_list.append(row_zyx)
        for y in range(4):
            row_zyx = []
            for i in range(4):
                row_zyx.append((i,y,i))
            all_row_zyx_list.append(row_zyx)
            row_zyx = []
            for i in range(4):
                row_zyx.append((3 - i,y,i))
            all_row_zyx_list.append(row_zyx)
        for x in range(4):
            row_zyx = []
            for i in range(4):
                row_zyx.append((i,i,x))
            all_row_zyx_list.append(row_zyx)
            row_zyx = []
            for i in range(4):
                row_zyx.append((3 - i,i,x))
            all_row_zyx_list.append(row_zyx)
        #立体斜め
        row_zyx = []
        for i in range(4):
            row_zyx.append((i,i,i))
        all_row_zyx_list.append(row_zyx)
        row_zyx = []
        for i in range(4):
            row_zyx.append((3 - i,i,i))
        all_row_zyx_list.append(row_zyx)
        row_zyx = []
        for i in range(4):
            row_zyx.append((i,3 - i,i))
        all_row_zyx_list.append(row_zyx)
        row_zyx = []
        for i in range(4):
            row_zyx.append((3 - i,3 - i,i))
        all_row_zyx_list.append(row_zyx)
        MyAI.ALL_ROW_XYZ_List = all_row_zyx_list

    
    # 発見した最初の空地の座標を返す。なければ(-1,-1,-1)。3つ配置してある前提で探すと即勝利点が取得できる。
    def check_emptyspot_in_row(self, idx_check_target_rowType, idx_targetKey_z, idx_targetKey_y, idx_targetKey_x) -> Tuple[int,int,int]: # z,y,xの順
        # 指定された行に空きがあるかどうかを確認し、その座標を返す
        if(idx_check_target_rowType == MyAI.IDX_check_target_rowListX): # x方向
            for x in range(4):
                if(self.board[idx_targetKey_z][idx_targetKey_y][x] == 0):
                    return (idx_targetKey_z, idx_targetKey_y, x)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListY): # y方向
            for y in range(4):
                if(self.board[idx_targetKey_z][y][idx_targetKey_x] == 0):
                    return (idx_targetKey_z, y, idx_targetKey_x)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListZ): # z方向    
            for z in range(4):
                if(self.board[z][idx_targetKey_y][idx_targetKey_x] == 0):
                    return (z, idx_targetKey_y, idx_targetKey_x)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListXDiagnal): # x固定した方向
            if(idx_targetKey_y == idx_targetKey_z):
                for i in range(4):
                    if(self.board[i][i][idx_targetKey_x] == 0):
                        return (i, i, idx_targetKey_x)
            if(idx_targetKey_y == 3 - idx_targetKey_z):
                for i in range(4):
                    if(self.board[3 - i][i][idx_targetKey_x] == 0):
                        return (3 - i, i, idx_targetKey_x)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListYDiagnal): # y固定した方向
            if(idx_targetKey_x == idx_targetKey_z):
                for i in range(4):
                    if(self.board[i][idx_targetKey_y][i] == 0):
                        return (i, idx_targetKey_y, i)
            if(idx_targetKey_x == 3 - idx_targetKey_z):
                for i in range(4):
                    if(self.board[3 - i][idx_targetKey_y][i] == 0):
                        return (3 - i, idx_targetKey_y, i)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListZDiagnal): # z固定した方向
            if(idx_targetKey_x == idx_targetKey_y):
                for i in range(4):
                    if(self.board[idx_targetKey_z][i][i] == 0):
                        return (idx_targetKey_z, i, i)
            if(idx_targetKey_x == 3 - idx_targetKey_y):
                for i in range(4):
                    if(self.board[idx_targetKey_z][3 - i][i] == 0):
                        return (idx_targetKey_z, 3 - i, i)
        elif(idx_check_target_rowType == MyAI.IDX_check_target_rowListCrossDiagnal): # 立体斜め
            if(idx_targetKey_x == idx_targetKey_y and idx_targetKey_y == idx_targetKey_z):
                for i in range(4):
                    if(self.board[i][i][i] == 0):
                        return (i, i, i)
            if(idx_targetKey_x == idx_targetKey_y and idx_targetKey_y == 3 - idx_targetKey_z):
                for i in range(4):
                    if(self.board[3 - i][i][i] == 0):
                        return (3 - i, i, i)
            if(idx_targetKey_x == 3 - idx_targetKey_y and idx_targetKey_y == idx_targetKey_z):
                for i in range(4):
                    if(self.board[i][3 - i][i] == 0):
                        return (i, 3 - i, i)
            if(idx_targetKey_x == 3 - idx_targetKey_y and idx_targetKey_y == 3 - idx_targetKey_z):
                for i in range(4):
                    if(self.board[3 - i][3 - i][i] == 0):
                        return (3 - i, 3 - i, i)
        return (-1,-1,-1) # 空きなし
                                        
        
    IDX_check_target_rowListX : int = 0
    IDX_check_target_rowListY : int = 1
    IDX_check_target_rowListZ : int = 2
    IDX_check_target_rowListXDiagnal : int = 3
    IDX_check_target_rowListYDiagnal : int = 4
    IDX_check_target_rowListZDiagnal : int = 5
    IDX_check_target_rowListCrossDiagnal : int = 6

    def init_memoryST_winInstant_3Dpoints(self):
        self.memoryST_winInstant_3Dpoints = []
        check_target_rowDict : dict[str,int] ={}
        basekey_list : list[int] = []

        ## check_target_rowListの初期化。
        for idx_check_target_rowType in range(7):
            for idx_targetKey_z in range(4):
                for idx_targetKey_y in range(4):
                    for idx_targetKey_x in range(4):
                        basekey_for_check = self.get_basekey_for_check(idx_check_target_rowType, idx_targetKey_z, idx_targetKey_y, idx_targetKey_x)
                        basekey_list.append(basekey_for_check)
                        for stoneType in range(3): # 1=黒,2=白
                            key_for_check = self.get_key_for_check(idx_check_target_rowType, idx_targetKey_z, idx_targetKey_y, idx_targetKey_x ,stoneType)
                            check_target_rowDict[key_for_check] = 0

#        print(check_target_rowDict)
        # 勝利ルートについて全通り探査する
        for x in range(4):
            for y in range(4):
                for z in range(4):
                    v = self.board[z][y][x]
                    # z方向の集計
                    key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListZ, 0 , y, x ,v)
                    cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                    check_target_rowDict[key_for_check] = cnt+1

                    # y方向の集計
                    key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListY, z , 0, x ,v)
                    cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                    check_target_rowDict[key_for_check] = cnt+1

                    # x方向の集計
                    key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListX, z , y, 0 ,v)
                    cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                    check_target_rowDict[key_for_check] = cnt+1
                    
                    # z固定した斜め集計
                    if(x == y):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListZDiagnal, z , 0, 0 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(x == 3 - y):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListZDiagnal, z , 0, 3 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1

                    # y固定した斜め集計
                    if(x == z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListYDiagnal, 0 , y, 0 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(x == 3 - z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListYDiagnal, 0 , y, 3 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1

                    # x固定した斜め集計
                    if(y == z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListXDiagnal, 0 , 0, x ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(y == 3 - z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListXDiagnal, 0 , 3, x ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    
                    # 立体斜め集計
                    if(x == y and y == z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListCrossDiagnal, 0 , 0, 0 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(x == y and y == 3 - z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListCrossDiagnal, 0 , 3, 3 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(x == 3 - y and y == z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListCrossDiagnal, 0 , 3, 0 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    if(x == 3 - y and y == 3 - z):
                        key_for_check = self.get_key_for_check(MyAI.IDX_check_target_rowListCrossDiagnal, 0 , 0, 3 ,v)
                        cnt = check_target_rowDict[key_for_check] ## これまでのカウント結果
                        check_target_rowDict[key_for_check] = cnt+1
                    
        already_double_row_check_list = []
        # 3つ以上揃っているものを勝利点として記憶する
        for basekey in basekey_list:
            key_for_check = basekey + 0
            empty_cnt = check_target_rowDict[key_for_check]

            for stoneType in [1,2]: # 1=黒,2=白
                key_for_check = basekey + stoneType
                cnt = check_target_rowDict[key_for_check]
                if(cnt == 3 and empty_cnt == 1):
                    ##print(f"WinInstant found! key:{key_for_check} cnt:{cnt} empty_cnt:{empty_cnt}")
                    idx_check_target_rowType = (basekey // 10000) % 10
                    idx_targetKey_z = (basekey // 1000) % 10
                    idx_targetKey_y = (basekey // 100) % 10
                    idx_targetKey_x = (basekey // 10) % 10
                    ##print(f"  -> rowType:{idx_check_target_rowType} z:{idx_targetKey_z} y:{idx_targetKey_y} x:{idx_targetKey_x} stoneType:{stoneType}")
                    z,y,x = self.check_emptyspot_in_row(idx_check_target_rowType, idx_targetKey_z, idx_targetKey_y, idx_targetKey_x);
                    if(z == -1):
                        print("  -> あるはずの空きがない。ERR596")
                        print(idx_check_target_rowType, idx_targetKey_z, idx_targetKey_y, idx_targetKey_x)
                    #即勝利点を記憶
                    if(stoneType == self.myPlayer):
                        self.memoryST_winInstant_3Dpoints.append((z,y,x))
                        ##print(f"  -> 勝点の空き座標は(z,y,x)=({z},{y},{x})")
                    elif(stoneType == self.opponentPlayer):
                        self.memoryST_loseInstant_3Dpoints.append((z,y,x))
                        ##print(f"  -> 負点の空き座標は(z,y,x)=({z},{y},{x})")
                elif(cnt == 4):
                    ## 本来ありえない。複数行既にそろっているチェック(学習用)
                    if(basekey not in already_double_row_check_list):
                        ## これは複数行勝っているというあり得ない状態のチェック。なので勝行・負行どちらでもかまわない。
                        already_double_row_check_list.append(basekey)
                    ##本来あり得ないが既に勝利している場合(学習用)
                    if(stoneType == self.myPlayer):
                        self.already_win_flg = True
                    else:
                        self.already_lose_flg = True
        if(len(already_double_row_check_list) >=2 ):
            self.already_double_row_flg = True

    def is_posible_to_place(self, z, y, x) -> bool:
        if(z < 0 or z > 3 or y < 0 or y > 3 or x < 0 or x > 3):
            return False
        if(self.board[z][y][x] != 0):
            return False
        if(z == 0):
            return True
        if(self.board[z-1][y][x] == 0):
            return False
        return True
    
    
    # 置いたらダブルリーチになる点を取得する関数。
    def init_memoryST_doubleReach_3Dpoints(self):
        self.memoryST_doubleReach_possible_3Dpoints = []
        self.memoryST_doubleReach_not_possible_3Dpoints = []
        self.memoryST_opponent_doubleReach_possible_3Dpoints = []
        self.memoryST_opponent_doubleReach_not_possible_3Dpoints = []
        for z, y, x in [(z,y,x) for z in range(4) for y in range(4) for x in range(4)]:
            if(self.board[z][y][x] == 0):
                effective_row_zyx_list = self.get_effective_row_zyx_list(z, y, x)
                reach_cnt = 0
                opponent_reach_cnt = 0
                for effective_row_zyx in effective_row_zyx_list:
                    cnt = 0
                    opponent_cnt = 0
                    reach_flg = False
                    for(z1, y1, x1) in effective_row_zyx:
                        if self.board[z1][y1][x1] == self.myPlayer:
                            cnt += 1
                        elif self.board[z1][y1][x1] == self.opponentPlayer:
                            opponent_cnt += 1
                            
                        # チェック対象以外に空があるということは他の2か所が同じ石の場合、リーチ可能性あり。そのフラグをonにする。
                        elif self.board[z1][y1][x1] == 0 and (z*100 + y*10 + x != z1*100 + y1*10 + x1):
                            if self.is_posible_to_place(z1, y1, x1) == True:
                                reach_flg = True
                    ## 影響行で2つ自石がある場合リーチ対象
                    if(cnt == 2 and reach_flg == True):
                        reach_cnt += 1
                    ## 影響行で2つ相手石がある場合リーチ対象
                    if(opponent_cnt == 2 and reach_flg == True):
                        opponent_reach_cnt += 1

                if(reach_cnt >= 2):
                    if(self.is_posible_to_place(z, y, x) == True):
                        self.memoryST_doubleReach_possible_3Dpoints.append((z,y,x))
                    else:
                        self.memoryST_doubleReach_not_possible_3Dpoints.append((z,y,x))
                if(opponent_reach_cnt >= 2):
                    if(self.is_posible_to_place(z, y, x) == True):
                        self.memoryST_opponent_doubleReach_possible_3Dpoints.append((z,y,x))
                    else:
                        self.memoryST_opponent_doubleReach_not_possible_3Dpoints.append((z,y,x))

            #各位置について、置いたら即勝利点が2つ以上になるかを確認する。
        
    ## 論理的着手可能点pr1を計算する。
    def init_logical_pr1_possible_3Dpoints(self):
        self.logical_pr1_possible_3Dpoints = []
        for z,y,x in self.memoryST_physical_possible_3Dpoints:
            # 自分の勝利点ではない (これは事前に探索済みのため省略)
            # その上(z+1)が相手の勝利着手点ではない。
         
            #print("計算確認1↓")
            #print(self.memoryST_loseInstant_3Dpoints)
            #print(f"z,y,x={z},{y},{x}")
            #print("-")
            #print(self.memoryLT_losing_3Dpoints)
            #print("^^^")
         
            if(z < 3):
                if( (z+1,y,x) in self.memoryST_loseInstant_3Dpoints):
                    
                    continue
                if( (z+1,y,x) in self.memoryLT_losing_3Dpoints):
                    continue
            self.logical_pr1_possible_3Dpoints.append((z,y,x))
        print(f"init_logical_pr1_possible_3Dpoints: {self.logical_pr1_possible_3Dpoints}")
        return
    ##
    def get_empty_board(self) -> List[List[List[int]]]:
        board = []
        for z in range(4):
            row_y = []
            for y in range(4):
                row_x = []
                for x in range(4):
                    row_x.append(0)
                row_y.append(row_x)
            board.append(row_y)
        return board
        
    
    ################　以下はテスト用の関数 ######################
    # 最大座標配置
    def place_max(self, list:Tuple[int,int,int]) -> Tuple[int,int]:
        tmp_len = len(list)
        if(tmp_len != 0):
            z,y,x = list[tmp_len -1]
        return (z,y,x)

    def test_put(self, x:int,y:int):
        #x,y指定したときの最大の配置可能なzを取得する。
        min_z = 99
        for tmp_z in range(4):
            if(self.board[tmp_z][y][x] == 0):
                if min_z > tmp_z:
                    min_z = tmp_z
        if min_z == 99 :
            print(f"配置不能({x},{y})")
        else:
            print(f"配置OK({x},{y})")
            self.board[min_z][y][x] = self.myPlayer

        # 手順入れ替え
        tmp_myPlayer = self.myPlayer
        tmp_opponentPlayer = self.opponentPlayer
        self.opponentPlayer = tmp_myPlayer
        self.myPlayer = tmp_opponentPlayer


    # x,yを渡してboardに石を配置するテスト用プログラム。
    def do_test_put(self):
        self.test_put(0, 0)
        self.test_put(3, 0)
        self.test_put(0, 3)
        self.test_put(0, 1)
        self.test_put(3, 3)
        self.test_put(1, 1)
        self.test_put(2, 1)
        self.test_put(1, 3)
        self.test_put(1, 0)
        self.test_put(1, 1)
        self.test_put(2, 1)
        self.test_put(1, 1)
        self.test_put(1, 1)
        self.test_put(2, 1)
        self.test_put(2, 1)