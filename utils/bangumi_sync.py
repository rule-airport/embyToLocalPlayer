import os
import re

from utils.configs import configs, MyLogger

logger = MyLogger()


def bangumi_sync(emby, bgm, emby_eps: list = None, emby_ids: list = None):
    from utils.bangumi_api import BangumiApiEmbyVer
    from utils.emby_api import EmbyApi
    bgm: BangumiApiEmbyVer
    emby: EmbyApi

    item_infos = emby_eps if emby_eps else [emby.get_item(i) for i in emby_ids]
    item_info = item_infos[0]
    if item_info['Type'] != 'Episode':
        logger.info('bgm: episode support only, skip')
        return

    season_num = item_info['ParentIndexNumber']
    index_key = 'index' if emby_eps else 'IndexNumber'
    ep_nums = [i[index_key] for i in item_infos]
    if season_num == 0 or 0 in ep_nums:
        logger.error(f'bgm: {season_num=} {ep_nums=} contain zero, skip')
        return
    series_id = item_info['SeriesId']
    series_info = emby.get_item(series_id)
    genres = series_info['Genres']
    gen_re = configs.raw.get('bangumi', 'genres', fallback='动画|anime')
    if not re.search(gen_re, ''.join(genres), flags=re.I):
        logger.error(f'bgm: {genres=} not match {gen_re=}, skip')
        return

    premiere_date = series_info['PremiereDate']
    emby_title = series_info['Name']
    ori_title = series_info.get('OriginalTitle', '')
    bgm_data = bgm.emby_search(title=emby_title, ori_title=ori_title, premiere_date=premiere_date)
    if not bgm_data:
        logger.error('bgm: bgm_data not found, skip')
        return

    bgm_data = bgm_data[0]
    if bgm.title_diff_ratio(title=emby_title, ori_title=ori_title, bgm_data=bgm_data) < 0.5:
        logger.error('bgm: bgm_data not match, skip')
        return

    subject_id = bgm_data['id']
    bgm_se_id, bgm_ep_ids = bgm.get_target_season_episode_id(
        subject_id=subject_id, target_season=season_num, target_ep=ep_nums)
    if not bgm_ep_ids:
        logger.info(f'bgm: {subject_id=} {season_num=} {ep_nums=}, not exists or too big, skip')
        return

    # bgm 同季第二部分的上映时间和 emby 的季上映时间对不上，故放弃。
    # if not emby_bgm_season_date_check(emby_se_info, bgm_se_info):
    #     logger.info(f'bgm: season_date_check failed, skip)
    #     return

    logger.info(f'bgm: get {bgm_data["name"]} S0{season_num}E{ep_nums} https://bgm.tv/subject/{bgm_se_id}')
    for bgm_ep_id, ep_num in zip(bgm_ep_ids, ep_nums):
        bgm.mark_episode_watched(subject_id=bgm_se_id, ep_id=bgm_ep_id)
        logger.info(f'bgm: sync {ori_title} S0{season_num}E{ep_num} https://bgm.tv/ep/{bgm_ep_id}')


def bangumi_sync_main(eps_data: list = None, test=False, use_ini=False):
    if not eps_data and not use_ini and not test:
        raise ValueError('not eps_data and not test')
    from utils.bangumi_api import BangumiApiEmbyVer
    from utils.emby_api import EmbyApi
    bgm = BangumiApiEmbyVer(
        username=configs.raw.get('bangumi', 'username', fallback=''),
        private=configs.raw.getboolean('bangumi', 'private', fallback=True),
        access_token=configs.raw.get('bangumi', 'access_token', fallback=''),
        http_proxy=configs.script_proxy)
    if test:
        bgm.get_me()
        return bgm
    if use_ini:
        from embyBangumi.embyBangumi import emby_bangumi
        emby = emby_bangumi(get_emby=True)
    else:
        fist_ep = eps_data[0]
        server = fist_ep['server']
        if server == 'plex':
            logger.error(f'bangumi_sync_by_eps not support {server=}')
            return
        emby = EmbyApi(host=f"{fist_ep['scheme']}://{fist_ep['netloc']}",
                       api_key=fist_ep['api_key'],
                       user_id=fist_ep['user_id'],
                       http_proxy=configs.script_proxy
                       )
    bangumi_sync(emby=emby, bgm=bgm, emby_eps=eps_data)


if __name__ == '__main__':
    os.chdir('..')
    bangumi_sync_main(use_ini=True)