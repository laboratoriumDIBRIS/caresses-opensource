<?xml version="1.0" encoding="UTF-8" ?>
<Package name="Pictures" format_version="4">
    <Manifest src="manifest.xml" />
    <BehaviorDescriptions>
        <BehaviorDescription name="behavior" src="send-by-email" xar="behavior.xar" />
        <BehaviorDescription name="behavior" src="send-by-telegram" xar="behavior.xar" />
        <BehaviorDescription name="behavior" src="play-shutter-sound" xar="behavior.xar" />
        <BehaviorDescription name="behavior" src="delete-picture" xar="behavior.xar" />
        <BehaviorDescription name="behavior" src="list-pictures" xar="behavior.xar" />
    </BehaviorDescriptions>
    <Dialogs />
    <Resources>
        <File name="camera1" src="play-shutter-sound/camera1.ogg" />
    </Resources>
    <Topics />
    <IgnoredPaths />
    <Translations auto-fill="en_US">
        <Translation name="translation_en_US" src="translations/translation_en_US.ts" language="en_US" />
    </Translations>
</Package>
