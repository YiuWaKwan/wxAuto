# coding: utf-8
#
import os

from lib.ModuleConfig import ConfAnalysis

BASEDIR = os.getcwd()
configFile = '%s/conf/moduleConfig.conf' % BASEDIR


class WxElementConf(object):
    logger = None

    def __init__(self, logger):
        self.logger = logger

    confAllItems = ConfAnalysis(logger, configFile)
    wxVersion = confAllItems.getOneOptions('wxVersion', 'version')
    wxElementConfFile = '%s/conf/wxElementId%s.conf' % (BASEDIR, wxVersion)
    wxElementConfItems = ConfAnalysis(logger, wxElementConfFile)
    # 系统
    ## 更新提醒模块
    needUpdate = wxElementConfItems.getOneOptions('system', 'needUpdate')
    cancelUpdate = wxElementConfItems.getOneOptions('system', 'cancelUpdate')
    cancelTips = wxElementConfItems.getOneOptions('system', 'cancelTips')
    cancelUpdateConfirm = wxElementConfItems.getOneOptions('system', 'cancelUpdateConfirm')
    wxDataVolume = wxElementConfItems.getOneOptions('system', 'wxDataVolume')
    manageDataVol = wxElementConfItems.getOneOptions('system', 'manageDataVol')
    manageChatData = wxElementConfItems.getOneOptions('system', 'manageChatData')
    manageDataDel = wxElementConfItems.getOneOptions('system', 'manageDataDel')
    allChckItem = wxElementConfItems.getOneOptions('system', 'allChckItem')
    manageDataDelFin = wxElementConfItems.getOneOptions('system', 'manageDataDelFin')
    nothingDel = wxElementConfItems.getOneOptions('system', 'nothingDel')
    appDetail = wxElementConfItems.getOneOptions('system', 'appDetail')
    totalSize = wxElementConfItems.getOneOptions('system', 'totalSize')
    textViewClassName = wxElementConfItems.getOneOptions('system', 'textViewClassName')

    #复用元素
    tishi = wxElementConfItems.getOneOptions('loginElementList', 'tishi')
    wo_shezhi = wxElementConfItems.getOneOptions('loginElementList', 'wo_shezhi')
    qiehuanyuyin = wxElementConfItems.getOneOptions('loginElementList', 'qiehuanyuyin')
    fasonggengduo = wxElementConfItems.getOneOptions('loginElementList', 'fasonggengduo')
    tuichu = wxElementConfItems.getOneOptions('loginElementList', 'tuichu')
    quxiao = wxElementConfItems.getOneOptions('loginElementList', 'quxiao')
    wo_shezhi_tuichu = wxElementConfItems.getOneOptions('loginElementList', 'wo_shezhi_tuichu')
    yourendenglu = wxElementConfItems.getOneOptions('loginElementList', 'yourendenglu')
    wo = wxElementConfItems.getOneOptions('loginElementList', 'wo')
    shurukuang = wxElementConfItems.getOneOptions('loginElementList', 'shurukuang')
    zitidaxiao = wxElementConfItems.getOneOptions('loginElementList', 'zitidaxiao')

    fanhui = wxElementConfItems.getOneOptions('momentsElementList', 'fanhui')
    fabiao = wxElementConfItems.getOneOptions('momentsElementList', 'fabiao')
    fileHelper = wxElementConfItems.getOneOptions('momentsElementList', 'fileHelper')
    sendMsg = wxElementConfItems.getOneOptions('momentsElementList', 'sendMsg')
    addToFriendList = wxElementConfItems.getOneOptions('momentsElementList', 'addToFriendList')

    bottom_me = wo
    wx_img_left = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_img_left')
    wx_img_more = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_img_more')
    friend_page = wxElementConfItems.getOneOptions('getFriendElementList', 'friend_page')
    RC_Con_Send = wxElementConfItems.getOneOptions('randomChat', 'RC_Con_Send')
    G_Index_Action = wxElementConfItems.getOneOptions('group', 'G_Index_Action')
    G_Person_Name_Open = wxElementConfItems.getOneOptions('group', 'G_Person_Name_Open')
    G_Grouo_Del = wxElementConfItems.getOneOptions('group', 'G_Group_Add')
    G_Friend_Search = wxElementConfItems.getOneOptions('group', 'G_Friend_Search')
    set_message_content = wxElementConfItems.getOneOptions('sendWxMessage', 'set_message_content')
    #复用原始 结束

    # 系统
    chushi_yuyan = wxElementConfItems.getOneOptions('loginElementList', 'chushi_yuyan')
    chushi_denglu = wxElementConfItems.getOneOptions('loginElementList', 'chushi_denglu')
    chushi_zhuce = wxElementConfItems.getOneOptions('loginElementList', 'chushi_zhuce')
    denglu_gengduo = wxElementConfItems.getOneOptions('loginElementList', 'denglu_gengduo')
    weixinhao = wxElementConfItems.getOneOptions('loginElementList', 'weixinhao')
    mimacuowu = tishi
    denglu = wxElementConfItems.getOneOptions('loginElementList', 'denglu')
    denglubyphone = wxElementConfItems.getOneOptions('loginElementList', 'denglubyphone')
    guanbi = wxElementConfItems.getOneOptions('loginElementList', 'guanbi')
    zairu = wxElementConfItems.getOneOptions('loginElementList', 'zairu')
    yingjilianxi=wxElementConfItems.getOneOptions('loginElementList', 'yingjilianxi')
    yingjilianxi_back=wxElementConfItems.getOneOptions('loginElementList', 'yingjilianxi_back')
    biaoqing=wxElementConfItems.getOneOptions('loginElementList', 'biaoqing')
    gengduoshuru=wxElementConfItems.getOneOptions('loginElementList', 'gengduoshuru')
    wxhao=wxElementConfItems.getOneOptions('loginElementList', 'wxhao')
    mimadenglu=wxElementConfItems.getOneOptions('loginElementList', 'mimadenglu')
    xiugaimima=wxElementConfItems.getOneOptions('loginElementList', 'xiugaimima')
    # 获取好友信息使用元素
    wx_main_nickname = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_main_nickname')
    wx_img_right = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_img_right')
    save_img_to_phone = wo_shezhi_tuichu
    back_to_wx_info = fanhui
    back_to_wx_me = fanhui
    bottom_contact = bottom_me
    wx_friend_item = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_friend_item')
    wx_friend_end_tag = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_friend_end_tag')
    search_content_box = shurukuang
    search_user_result = wx_img_left
    user_more_button = wx_img_more
    wx_friend_remark = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_friend_remark')
    wx_friend_id = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_friend_id')
    wx_friend_nickname = wxElementConfItems.getOneOptions('getFriendElementList', 'wx_friend_nickname')
    save_friend_headimg = wxElementConfItems.getOneOptions('getFriendElementList', 'save_friend_headimg')
    friend_sex = wxElementConfItems.getOneOptions('getFriendElementList', 'friend_sex')
    area_box = wo_shezhi
    area = wxElementConfItems.getOneOptions('getFriendElementList', 'area')
    home_page_wx = wo
    change_to_keyboard = qiehuanyuyin

    # 发送聊天消息（群聊、个人）
    set_nickname = shurukuang
    sousuokuangquxiao = wxElementConfItems.getOneOptions('sendWxMessage','sousuokuangquxiao')
    searchPageFlag = wxElementConfItems.getOneOptions('sendWxMessage','searchPageFlag')
    click_nickname = wx_img_left
    send_message = RC_Con_Send
    chat_nickname = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_nickname')
    chat_objectsend = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_objectsend')
    chat_addbutton = fasonggengduo
    windowname = wxElementConfItems.getOneOptions('sendWxMessage', 'windowname')
    checkbox = wxElementConfItems.getOneOptions('sendWxMessage', 'checkbox')
    send_file = fabiao
    oper_confirm = tuichu
    oper_once = wxElementConfItems.getOneOptions('sendWxMessage', 'oper_once')
    oper_cancel = quxiao
    oper_tips = wxElementConfItems.getOneOptions('sendWxMessage', 'oper_tips')
    file_button = wxElementConfItems.getOneOptions('sendWxMessage', 'file_button')
    file_button_item = wxElementConfItems.getOneOptions('sendWxMessage', 'file_button_item')
    at_nickname = wxElementConfItems.getOneOptions('sendWxMessage', 'at_nickname')
    at_search = wxElementConfItems.getOneOptions('sendWxMessage', 'at_search')
    detail_title = wo_shezhi
    chat_record_item = wo_shezhi_tuichu
    transpond_to_friend = wo_shezhi_tuichu  #转发给朋友
    multi_select = fabiao #多选
    chat_record_video_item = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_record_video_item')
    chat_record_video_pic_item = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_record_video_pic_item')
    download_picture = wxElementConfItems.getOneOptions('sendWxMessage', 'download_picture')
    chat_record_file_item = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_record_file_item')
    download_tips = wxElementConfItems.getOneOptions('sendWxMessage', 'download_tips')
    file_print = wxElementConfItems.getOneOptions('sendWxMessage', 'file_print')
    return_to_wx = wxElementConfItems.getOneOptions('sendWxMessage', 'return_to_wx')
    open_file_button = wxElementConfItems.getOneOptions('sendWxMessage', 'open_file_button')
    open_file_choose = wxElementConfItems.getOneOptions('sendWxMessage', 'open_file_choose')
    back_to_chat_button = fanhui
    back_to_at_button = wxElementConfItems.getOneOptions('sendWxMessage', 'back_to_at_button')
    chat_back_btn = wxElementConfItems.getOneOptions('sendWxMessage', 'chat_back_btn')
    #搜索相关
    searchText = shurukuang
    searchNickname = fileHelper
    searchErrorResult = wxElementConfItems.getOneOptions('search', 'searchErrorResult')

    # 修改微信好友备注
    friend_more = wx_img_more
    select_set_friend_remark = wo_shezhi_tuichu
    set_friend_remark = wxElementConfItems.getOneOptions('changFriendRemark', 'set_friend_remark')
    set_friend_remark_other = wxElementConfItems.getOneOptions('changFriendRemark', 'set_friend_remark_other')
    search_result_with_wxid=wxElementConfItems.getOneOptions('changFriendRemark','search_result_with_wxid')
    finish_update_remark = fabiao
    not_save_edit_result = quxiao
    remark_save_tips = tishi

    # 加好友
    AD_Index_Action = wxElementConfItems.getOneOptions('addFriend', 'AD_Index_Action')
    AD_Add_Action = wxElementConfItems.getOneOptions('addFriend', 'AD_Add_Action')
    AD_Set_Text = wxElementConfItems.getOneOptions('addFriend', 'AD_Set_Text')
    AD_Friend_Find_Info = wxElementConfItems.getOneOptions('addFriend', 'AD_Friend_Find_Info')
    AD_Friend_Not_Find = wxElementConfItems.getOneOptions('addFriend', 'AD_Friend_Not_Find')
    AD_Friend_Exists = wxElementConfItems.getOneOptions('addFriend', 'AD_Friend_Exists')
    AD_Back = wxElementConfItems.getOneOptions('addFriend', 'AD_Back')
    AD_Text_Back = AD_Back
    AD_Friend_Find = AD_Friend_Exists
    AD_Say_Hi = wxElementConfItems.getOneOptions('addFriend', 'AD_Say_Hi')
    AD_Hi_Send = wxElementConfItems.getOneOptions('group', 'G_Create_Confirm')
    AD_Frequent_Operate = wxElementConfItems.getOneOptions('addFriend','AD_Frequent_Operate')
    AD_Exception_Tips = wxElementConfItems.getOneOptions('addFriend','AD_Exception_Tips')
    AD_Mail_List = wxElementConfItems.getOneOptions('addFriend', 'AD_Mail_List')
    AD_No_Mail_List = wxElementConfItems.getOneOptions('addFriend', 'AD_No_Mail_List')
    AD_Bind_Phone = wxElementConfItems.getOneOptions('addFriend', 'AD_Bind_Phone')
    AD_Exist_Name = wxElementConfItems.getOneOptions('addFriend', 'AD_Exist_Name')
    AD_Wechat_Name = wxElementConfItems.getOneOptions('addFriend', 'AD_Wechat_Name')
    AD_To_Mail_List = wxElementConfItems.getOneOptions('addFriend', 'AD_To_Mail_List')
    AD_Sure_Mail_list = wxElementConfItems.getOneOptions('addFriend', 'AD_Sure_Mail_list')
    AD_Upload_Mail_List = wxElementConfItems.getOneOptions('addFriend', 'AD_Upload_Mail_List')
    AD_Wx_Name = wxElementConfItems.getOneOptions('addFriend', 'AD_Wx_Name')
    C_LOAD_CONTRACT = wxElementConfItems.getOneOptions('addFriend','C_LOAD_CONTRACT')
    C_LIST_TOP = wxElementConfItems.getOneOptions('addFriend','C_LIST_TOP')

    # # 养号聊天
    RC_Set_Text = shurukuang
    RC_Friend_Find = fileHelper
    RC_Con_Set_Text = set_message_content
    RC_Voice_Say = wxElementConfItems.getOneOptions('randomChat', 'RC_Voice_Say')
    RC_Change_Voice = qiehuanyuyin

    # 群
    ##一键拉群
    G_Group_MainCh_Fin = wxElementConfItems.getOneOptions('group', 'G_Group_MainCh_Fin')
    G_Group_Action = wxElementConfItems.getOneOptions('group', 'G_Group_Action')
    G_Friend_Not_Find = wxElementConfItems.getOneOptions('group', 'G_Friend_Not_Find')
    G_Friend_Find_Click = wxElementConfItems.getOneOptions('group', 'G_Friend_Find_Click')
    G_Friend_Find_Click_D = wxElementConfItems.getOneOptions('group', 'G_Friend_Find_Click_D')
    G_Create_Confirm = wxElementConfItems.getOneOptions('group', 'G_Create_Confirm')
    G_Info_Edit = wxElementConfItems.getOneOptions('group', 'G_Info_Edit')
    G_Group_Name = wxElementConfItems.getOneOptions('group', 'G_Group_Name')
    G_Group_Name_Set = wxElementConfItems.getOneOptions('group', 'G_Group_Name_Set')
    G_Group_Name_Save = G_Create_Confirm
    G_Notice = wxElementConfItems.getOneOptions('group', 'G_Notice')
    G_Notice_Set = wxElementConfItems.getOneOptions('group', 'G_Notice_Set')
    G_Notice_Save = G_Create_Confirm
    G_Notice_Send = G_Group_MainCh_Fin
    G_Person_Name = G_Group_Name
    G_Cont_List = G_Group_Name
    G_Cont_List_Open = G_Person_Name_Open
    G_Main_Name = G_Group_Name
    G_Main_Set = AD_Set_Text
    G_Main_Confirm = G_Group_MainCh_Fin
    G_Create_Fail = wxElementConfItems.getOneOptions('group','G_Create_Fail')
    G_Create_Fail_Confirm = G_Group_MainCh_Fin
    G_Friend_Item = wxElementConfItems.getOneOptions('group','G_Friend_Item')
    G_Friend_First = wxElementConfItems.getOneOptions('group','G_Friend_First')

    ##群加好友
    G_Group_Pick = wxElementConfItems.getOneOptions('group', 'G_Group_Pick')
    G_Group_PickName = wxElementConfItems.getOneOptions('group', 'G_Group_PickName')
    # G_Group_Info = wx_img_more
    G_Group_Add = wxElementConfItems.getOneOptions('group', 'G_Group_Add')
    G_Group_Add_Search = G_Friend_Search
    G_Group_Add_Confirm = G_Create_Confirm

    ##群删好友
    G_Group_Del = wo_shezhi_tuichu
    G_Group_Del_Search = wxElementConfItems.getOneOptions('group','G_Group_Del_Search')
    G_Group_Friend_Not_Find = wxElementConfItems.getOneOptions('group', 'G_Group_Friend_Not_Find')
    G_Group_Del_Confirm = G_Create_Confirm
    G_Group_Del_Fin = G_Group_MainCh_Fin

    ##群解散
    G_Group_Delete_An = G_Group_MainCh_Fin
    G_Del_OUT = wxElementConfItems.getOneOptions('group', 'G_Del_OUT')
    ##修改公告
    G_Group_Notice = wxElementConfItems.getOneOptions('group', 'G_Notice')
    G_Group_NoticeEdit = G_Create_Confirm
    G_Grpup_Notice_Set = wxElementConfItems.getOneOptions('group', 'G_Notice_Set')
    G_Group_Notice_Fin = G_Group_MainCh_Fin
    ##更换群主
    G_Group_MainCh_Search = wxElementConfItems.getOneOptions('group', 'G_Group_MainCh_Search')
    G_Group_MainCh_Find = wxElementConfItems.getOneOptions('group', 'G_Group_MainCh_Find')


    ##修改群主昵称
    G_Group_WxName_Set = AD_Set_Text
    G_Group_WxName_Confirm = G_Group_MainCh_Fin

    # 通过收藏发朋友圈
    tianjiashoucang = wx_img_more
    wenzikuang = wxElementConfItems.getOneOptions('momentsElementList', 'wenzikuang')
    zhiding = wo_shezhi_tuichu
    shoucangneirong = wxElementConfItems.getOneOptions('momentsElementList', 'shoucangneirong')
    queding = G_Group_MainCh_Fin
    tixing = yourendenglu
    wenzitixing = wxElementConfItems.getOneOptions('momentsElementList', 'wenzitixing')
    picAndVideo = wxElementConfItems.getOneOptions('momentsElementList', 'picAndVideo')
    picturesFolder = wxElementConfItems.getOneOptions('momentsElementList', 'picturesFolder')
    wztx = wxElementConfItems.getOneOptions('momentsElementList', 'wztx')
    msgList= wxElementConfItems.getOneOptions('momentsElementList', 'msgList')
    firstFav= wxElementConfItems.getOneOptions('momentsElementList', 'firstFav')
    favLink= wxElementConfItems.getOneOptions('momentsElementList', 'favLink')
    closeLink = fanhui

    #微信主页搜索按钮
    index_search=AD_Index_Action

    # 群发
    gs_new_1 = wxElementConfItems.getOneOptions('groupSent', 'gs_new_1')
    gs_new_2 = wxElementConfItems.getOneOptions('groupSent', 'gs_new_2')
    picture_dir = wxElementConfItems.getOneOptions('groupSent', 'picture_dir')
    picture_first = wxElementConfItems.getOneOptions('groupSent', 'picture_first')

