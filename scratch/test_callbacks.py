import re

with open('bot/handlers/management.py', 'r', encoding='utf-8') as f:
    content = f.read()

with open('bot/handlers/filter_fsm.py', 'r', encoding='utf-8') as f:
    content_fsm = f.read()

emitted = set(re.findall(r'callback_data=f?["\']([^"\']+)["\']', content + content_fsm))
handled_exact = set(re.findall(r'F\.data == ["\']([^"\']+)["\']', content + content_fsm))
handled_starts = set(re.findall(r'F\.data\.startswith\(["\']([^"\']+)["\']\)', content + content_fsm))

print("Total emitted callbacks:", len(emitted))
print("Handled exact count:", len(handled_exact))
print("Handled startswith count:", len(handled_starts))

unhandled = []
for cb in emitted:
    clean_prefix = cb.split('{')[0] if '{' in cb else cb
    if clean_prefix in handled_exact:
        continue
    if any(clean_prefix.startswith(sw) for sw in handled_starts):
        continue
    # Could be button_noop or similar
    if clean_prefix in ("noop", "hd_noop", "filter_noop", "fdetail_header", "hd_hub_header"):
        continue
    unhandled.append(cb)

if unhandled:
    print("Potential unhandled callbacks:", unhandled)
else:
    print("ALL EMITTED CALLBACKS ARE PROPERLY HANDLED!")
