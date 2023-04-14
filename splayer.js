/* Frontend helper functions for a browser-based spotify player*/

var spHeaders = [{
    name: "Authorization",
    value: 'Bearer ' + access_token
}];

playlist_id = -1
playlists = []
tracks = []


async function spGetPlaylistID(pln = 'FMizer') {
    /* gets Playlist id for pln*/
    await spGetPlaylists();

    for (var i = 0; i < playlists.length; i++) {
        if (playlists[i].name == pln)
            playlist_id = playlists[i].id;
        if (playlists[i].name == pln + "-History")
            playlistHistory_id = playlists[i].id;
    }
    if (playlist_id != "")
        await spGetPlaylistTracks();
}

async function spGetPlaylists(offset = 0) {
    /* gets Playlists for user*/
    if (offset == 0)
        playlists = [];
    let limit = 20;
    let uri = "https://api.spotify.com/v1/me/playlists?limit=" + limit + "&offset=" + offset;
    offset = Math.max(offset, 0);
    let data = {
        offset: offset,
        limit: limit
    };
    var total = 0;
    await reqHTTPA('GET', uri, data, spHeaders).then(function(result) {
        for (let i = 0; i < result.items.length; i++) {
            playlists.push({
                id: result.items[i].id,
                name: result.items[i].name,
                uri: result.items[i].uri
            });
        }
        total = result.total;
    });

    if (offset == 0) {
        let cnt = 0;
        while (total > playlists.length && cnt++ < 20) {
            offset = offset + limit;
            await spGetPlaylists(offset);
        };
    }
}

async function spGetPlaylistTracks(offset = 0) {
    /* gets Tracks for default Playlist*/
    if (offset == 0)
        tracks = [];

    let limit = 50;
    let uri = "https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks?offset=" + offset + "&limit=" + limit;
    offset = Math.max(offset, 0);
    let data = {
        fields: "total,items(track(id,name,uri))"
    };
    var total = 0;
    await reqHTTPA('GET', uri, data, spHeaders).then(function(result) {
        for (let i = 0; i < result.items.length; i++) {
            tracks.push({
                id: result.items[i].track.id,
                name: result.items[i].track.name,
                uri: result.items[i].track.uri
            });
        }
        total = result.total;
    });

    if (offset == 0) {
        let cnt = 0;
        while (total > playlists.length && cnt++ < 20) {
            offset = offset + limit;
            await spGetPlaylistTracks(offset);
        };
    }

}

async function spPlayerPlay(context_uri = "", offset = -1) {
    /* start playing Track (context_uri) */
    let uri = "https://api.spotify.com/v1/me/player/play?device_id=" + dev_id;

    if (playlist_id == '' || playlist_id == 'undefined')
        addToPlaylist(1);
    if (context_uri == "")
        context_uri = 'spotify:playlist:' + playlist_id;
    let data = {
        context_uri: context_uri
    };

    if (offset > -1)
        data.offset = {
            position: offset
        };
    reqHTTPA('PUT', uri, data, spHeaders);
}

async function spPlayerStart() {
    /* start Player */
    let uri = "https://api.spotify.com/v1/me/player";

    await spGetUserInfo();
    await spGetPlaylistID();

    let data = {};
    data = {
        device_ids: [dev_id],
        play: false
    };
    reqHTTPA('PUT', uri, data, spHeaders).then(function(result) {
        volTo(0, sp_volume);
        spPlayerPlay();
    });
}

async function spGetUserInfo() {
    /* get User Info from Spotify */
    let uri = "https://api.spotify.com/v1/me";
    let data = {};
    await reqHTTPA('GET', uri, data, spHeaders).then(async function(result) {
        userInfo = result;
        let uri2 = "https://www.fmizer.com/userInfo/index.php";
        let data2 = "station=" + newsfeed + "&userinfo=" + JSON.stringify(result);
        reqHTTPA('GET', uri2 + "?" + data2, data2);
    });
}

function spPlayerStop() {
    /* stop player */
    let uri = "https://api.spotify.com/v1/me/player/pause?device_id+" + dev_id;
    let data = {};
    reqHTTPA('PUT', uri, data, spHeaders);
}


function spRefreshToken() {
    /* Refresh Spotify token*/
    var uri = rf_url + "/refresh_token?refresh_token=" + refresh_token;
    var data = {};

    reqHTTPA('GET', uri, data, spHeaders).then(function(result) {
        access_token = result.access_token;
        spHeaders = [{
            name: "Authorization",
            value: 'Bearer ' + access_token
        }];
    });
}


function spVolDown(time = 1, vol = 0, steps = 10, decr = 0) {
    /* Volume down gradually in time, a little bit aleatory due to async  */
    sp.getVolume().then(current_volume => {
        if (current_volume > vol) {
            if (decr == 0)
                decr = Math.round((current_volume - vol) / steps * 100) / 100;
            sp.setVolume(Math.max(vol, current_volume - decr)).then(() => {
                setTimeout(function() {
                    volDown(time, vol, steps, decr);
                }, time / steps * 1000);
            });
        }
    });
}

function spVolUp(time = 1, vol = 0.8, steps = 10, incr = 0) {
    /* Volume up gradually, a little bit aleatory due to async  */
    if (audioQueue.length == 0)
        sp.getVolume().then(current_volume => {
            if (current_volume < vol) {
                if (incr == 0)
                    incr = Math.round((vol - current_volume) / steps * 100) / 100;
                sp.setVolume(Math.min(vol, current_volume + incr)).then(() => {
                    setTimeout(function() {
                        volUp(time, vol, steps, incr);
                    }, time / steps * 1000);
                });
            }
        });
}


function spVolTo(time = 1, vol = 0, steps = 10) {
    /* Set volume gradually, a little bit aleatory due to async  */
    sp.getVolume().then(current_volume => {
        if (current_volume > vol)
            spVolDown(time, vol, steps);
        else
            spVolUp(time, vol, steps);
    });
    return volume;
}

function setVol(percent) {
    /* set Volume to value from user input*/
    document.getElementById('volume').style.width = Math.round(percent * 100) + "%";
    return spVolTo(1, percent);
}
