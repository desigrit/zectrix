const $ = (id) => document.getElementById(id);
const appBase = document.querySelector('meta[name="app-base"]').content;
const appPath = (path) => appBase + path;
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let state;
let mode = 'calendar';
let lastDigest = '';
const dateFormat = (value, options) => new Intl.DateTimeFormat('en-US', {timeZone: state?.settings.timezone || 'America/Los_Angeles', ...options}).format(new Date(value));

function notice(text, error = false) {
  $('notice').hidden = !text;
  $('notice').textContent = text || '';
  $('notice').classList.toggle('error', error);
}

async function api(path, body, method = 'POST') {
  const headers = {'X-CSRF-Token': csrf};
  const options = {method, headers};
  if (body instanceof FormData) options.body = body;
  else if (method !== 'GET') { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body || {}); }
  const response = await fetch(appPath(path), options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request failed. Try again.');
  return data;
}

async function action(button, operation) {
  button.disabled = true;
  const previous = button.textContent;
  button.textContent = 'Working...';
  try {
    const result = await operation();
    if (result?.message) notice(result.message);
    await refreshStatus();
  } catch(error) { notice(error.message, true); }
  finally { button.disabled = false; button.textContent = previous; }
}

async function refreshStatus(initial = false) {
  state = await api(`/api/status?mode=${mode}`, null, 'GET');
  const example = mode !== 'calendar';
  const labels = {live:'Google Calendar connected',snapshot:'Saved calendar snapshot',offline:'Offline · saved calendar',unconnected:'Connect your calendar'};
  $('source-label').textContent = labels[state.source];
  document.querySelector('.source-state').classList.toggle('live', state.source === 'live');
  $('example-label').hidden = !example;
  $('shown-count').textContent = `${state.shown} of ${state.total} events shown`;
  $('preview-detail').textContent = `400 × 300 pixels · ${state.shown} events shown`;
  $('holiday-label').textContent = state.holiday ? `${state.holiday.name} · ${state.holiday.date.slice(5).replace('-', '/')}` : 'None available';
  $('timezone-label').textContent = state.settings.timezone.split('/').pop().replaceAll('_',' ');
  $('next-update').textContent = `Next check: ${dateFormat(state.next_update,{weekday:'short',hour:'numeric',minute:'2-digit'})}`;
  $('connection-heading').textContent = state.source === 'live' ? 'Calendar connected' : state.source === 'offline' ? 'Saved calendar available' : 'Calendar snapshot';
  $('connection-description').textContent = state.source === 'live' ? 'Changes are fetched once a day at midnight in your selected timezone.' : state.source === 'offline' ? state.error : 'This is your saved calendar. Connect Google in Settings to keep it updated automatically.';
  $('refresh').textContent = state.google_connected ? 'Refresh calendar' : 'Connect Google Calendar';
  const managedGoogle = state.google_auth_method === 'service_account';
  $('google-form').hidden = managedGoogle;
  $('google-managed').hidden = !managedGoogle;
  $('google-managed-description').textContent = state.source === 'live'
    ? 'Connected through this Pi\'s existing calendar connection. Calendar access is read-only. No Google sign-in is needed.'
    : 'This connection is managed on the Pi. If refresh fails, check that the Pi can access the selected Google calendar.';
  $('last-fetched').textContent = state.fetched_at ? `Saved ${dateFormat(state.fetched_at,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}` : 'No calendar saved yet.';
  $('event-count').textContent = `(${state.shown})`;
  $('event-list').replaceChildren(...state.rows.map(row => {
    const li=document.createElement('li');
    li.append(document.createTextNode(row.title));
    const detail=document.createElement('span');
    detail.textContent=`${row.date} · ${row.all_day ? 'All day' : row.time}`;
    li.append(detail);
    return li;
  }));
  if (state.device_seen.seen_at) {
    $('device-status').textContent = `Last confirmed display: ${dateFormat(state.device_seen.seen_at,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}. The Note wakes at its next scheduled check-in.`;
  }
  const key=`${mode}:${state.digest}`;
  if (key !== lastDigest) { $('screen').src=appPath(`/api/frame.png?mode=${mode}&v=${state.digest}`); lastDigest=key; }
  $('download-png').href=appPath(`/api/frame.png?mode=${mode}&native=1&download=1`);
  $('download-bin').href=appPath(`/api/frame.bin?mode=${mode}`);
  $('holiday-coverage').textContent=`Saved Indian holiday dates through ${state.holiday_coverage || 'the next available date'}. Dates refresh when Google is connected.`;
  if (initial) {
    $('calendar-id').value=state.settings.calendar_id;
    $('timezone').value=state.settings.timezone;
    $('device-url').value=state.settings.device_url;
  }
}

function showSettings(open) {
  $('settings').hidden=!open;
  $('settings-toggle').setAttribute('aria-expanded',String(open));
  if(open) $('settings').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
}
$('settings-toggle').onclick=()=>showSettings($('settings').hidden);
$('settings-close').onclick=()=>{showSettings(false);$('settings-toggle').focus();};
$('mode').onchange=async()=>{mode=$('mode').value;try{await refreshStatus();}catch(error){notice(error.message,true);}};
for(const size of ['one','two']) $('scale-'+size).onclick=()=>{
  $('device-frame').classList.toggle('actual-size',size==='one');
  $('scale-one').setAttribute('aria-pressed',String(size==='one'));
  $('scale-two').setAttribute('aria-pressed',String(size==='two'));
};
$('refresh').onclick=()=>{
  if(!state?.google_connected){showSettings(true);return;}
  action($('refresh'),()=>api('/api/refresh'));
};
$('google-form').onsubmit=(event)=>{event.preventDefault();action(event.submitter,()=>api('/api/google/client',new FormData(event.target)));};
$('preferences-form').onsubmit=(event)=>{event.preventDefault();action(event.submitter,()=>api('/api/settings',{calendar_id:$('calendar-id').value,timezone:$('timezone').value}));};
$('legacy-form').onsubmit=(event)=>{event.preventDefault();action(event.submitter,()=>api('/api/settings',{device_url:$('device-url').value}));};
$('check-device').onclick=()=>action($('check-device'),()=>api('/api/device/check'));
$('send-device').onclick=()=>action($('send-device'),()=>api('/api/device/send'));
$('pair-toggle').onclick=async()=>{
  const open=$('pairing').hidden;
  if(open){try{const info=await api('/api/pairing',null,'GET');$('pair-url').value=info.controller_url;$('pair-key').value=info.device_key;}catch(error){notice(error.message,true);return;}}
  $('pairing').hidden=!open;
  $('pair-toggle').setAttribute('aria-expanded',String(open));
  $('pair-toggle').textContent=open?'Hide pairing details':'Show pairing details';
};
$('copy-key').onclick=async()=>{try{await navigator.clipboard.writeText($('pair-key').value);notice('Device key copied.');}catch{notice('Clipboard access was unavailable. Select the device key and copy it manually.',true);$('pair-key').type='text';$('pair-key').select();}};
const messages={'google-connected':'Google Calendar connected and refreshed.','google-client-needed':'Choose your Google Desktop OAuth client JSON in Settings first.','google-expired':'The Google sign-in expired. Connect again.','google-cancelled':'Google connection was cancelled. Your snapshot is still available.','google-failed':'Google connection did not finish. Check the client configuration, then connect again.'};
const query=new URLSearchParams(location.search);
if(messages[query.get('notice')]){notice(messages[query.get('notice')],query.get('notice')!=='google-connected');history.replaceState({},'',location.pathname);}
refreshStatus(true).catch(error=>notice(`Could not load the calendar. ${error.message}`,true));
setInterval(()=>refreshStatus().catch(()=>notice('The controller is unreachable. Check that the Pi is on your network, then reload this page.',true)),60000);
