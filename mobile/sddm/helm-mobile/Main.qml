import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root

    width: 1920
    height: 1080

    color: "#02070B"
    focus: true

    property string currentTime: ""
    property string currentDate: ""
    property bool pulseState: false
    property bool authenticating: false

    function updateClock() {
        const now = new Date()

        currentTime = Qt.formatTime(
            now,
            "HH:mm:ss"
        )

        currentDate = Qt.formatDate(
            now,
            "yyyy-MM-dd"
        )
    }

    function submitLogin() {
        if (authenticating) {
            return
        }

        const username = usernameField.text.trim()

        if (username.length === 0) {
            statusText.text =
                "STATUS: OPERATOR IDENTIFIER REQUIRED"

            usernameField.forceActiveFocus()
            return
        }

        if (passwordField.text.length === 0) {
            statusText.text =
                "STATUS: CREDENTIAL REQUIRED"

            passwordField.forceActiveFocus()
            return
        }

        authenticating = true

        statusText.text =
            "STATUS: AUTHENTICATING OPERATOR..."

        sddm.login(
            username,
            passwordField.text,
            Math.max(
                0,
                sessionBox.currentIndex
            )
        )
    }

    Component.onCompleted: {
        updateClock()

        if (usernameField.text.length > 0) {
            passwordField.forceActiveFocus()
        } else {
            usernameField.forceActiveFocus()
        }
    }

    Connections {
        target: sddm

        function onLoginSucceeded() {
            statusText.text =
                "STATUS: ACCESS GRANTED"

            authenticating = true
        }

        function onLoginFailed() {
            authenticating = false
            passwordField.text = ""

            statusText.text =
                "STATUS: ACCESS DENIED // RETRY"

            passwordField.forceActiveFocus()
        }

        function onInformationMessage(message) {
            if (message && message.length > 0) {
                statusText.text =
                    "STATUS: " + message.toUpperCase()
            }
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true

        onTriggered: {
            root.updateClock()
            root.pulseState = !root.pulseState
        }
    }

    Shortcut {
        sequence: "Escape"

        onActivated: {
            passwordField.text = ""
            statusText.text =
                "STATUS: CREDENTIAL CHANNEL CLEARED"
        }
    }

    Image {
        anchors.fill: parent

        source: Qt.resolvedUrl(
            "wallpaper.svg"
        )

        fillMode: Image.PreserveAspectCrop
        smooth: true
        asynchronous: false
        cache: true
    }

    Rectangle {
        anchors.fill: parent
        color: "#1600070B"
    }

    Repeater {
        model: Math.ceil(
            root.height / 4
        )

        delegate: Rectangle {
            required property int index

            x: 0
            y: index * 4

            width: root.width
            height: 1

            color: "#0800E8FF"
        }
    }

    Rectangle {
        x: 0
        y: -4

        width: root.width
        height: 3

        color: "#2442E8FF"

        SequentialAnimation on y {
            loops: Animation.Infinite

            NumberAnimation {
                from: -4
                to: root.height + 4
                duration: 9000
                easing.type: Easing.Linear
            }

            PauseAnimation {
                duration: 500
            }
        }
    }

    Rectangle {
        anchors.fill: parent

        color: "transparent"
        border.color: "#2242E8FF"
        border.width: 1
    }

    Rectangle {
        id: identityPanel

        anchors.left: parent.left
        anchors.top: parent.top

        anchors.leftMargin: 38
        anchors.topMargin: 38

        width: Math.min(
            570,
            root.width * 0.43
        )

        height: 166

        color: "#FF02070B"
        border.color: "#42E8FF"
        border.width: 1

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            width: 7
            color: "#42E8FF"
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top

            anchors.leftMargin: 22
            anchors.rightMargin: 18
            anchors.topMargin: 17

            height: 1
            color: "#6642E8FF"
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top

            anchors.leftMargin: 28
            anchors.rightMargin: 18
            anchors.topMargin: 28

            spacing: 7

            Text {
                text:
                    "HELM MOBILE // ACCESS GATE"

                color: "#42E8FF"

                font.family: "Hack"
                font.pixelSize: 18
                font.bold: true
                font.letterSpacing: 1.2
            }

            Text {
                text:
                    sddm.hostName.toUpperCase()
                    + "  ·  FIELD NODE 01"

                color: "#D7F9FF"

                font.family: "Hack"
                font.pixelSize: 12
                font.bold: true
                font.letterSpacing: 0.65
            }

            Text {
                text:
                    "SDDM AUTHENTICATION"
                    + "  //  NATIVE CHANNEL"

                color: "#78A8B3"

                font.family: "Hack"
                font.pixelSize: 11
                font.letterSpacing: 0.35
            }

            Text {
                text:
                    "SYSTEM READY"
                    + "  ·  AUTHENTICATION REQUIRED"

                color: "#3EC9DC"

                font.family: "Hack"
                font.pixelSize: 10
                font.letterSpacing: 0.3
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            anchors.rightMargin: 14
            anchors.bottomMargin: 12

            width: 62
            height: 3

            color: "#42E8FF"
        }
    }

    Rectangle {
        id: loginCard

        anchors.centerIn: parent
        anchors.verticalCenterOffset: 22

        width: 440
        height: 484

        color: "#FA02070B"

        border.color:
            root.pulseState
            ? "#7542E8FF"
            : "#4942E8FF"

        border.width: 1
        radius: 2

        Behavior on border.color {
            ColorAnimation {
                duration: 450
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top

            height: 4
            color: "#42E8FF"
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 10

            color: "transparent"
            border.color: "#1642E8FF"
            border.width: 1
        }

        ColumnLayout {
            anchors.fill: parent

            anchors.leftMargin: 48
            anchors.rightMargin: 48
            anchors.topMargin: 32
            anchors.bottomMargin: 28

            spacing: 10

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 18

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter

                    text:
                        "SECURE OPERATOR CHANNEL"

                    color: "#42E8FF"

                    font.family: "Hack"
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 0.8
                }

                Text {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter

                    text: "01"

                    color: "#5A8791"

                    font.family: "Hack"
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Item {
                Layout.alignment:
                    Qt.AlignHCenter

                Layout.preferredWidth: 88
                Layout.preferredHeight: 88

                Rectangle {
                    anchors.fill: parent

                    radius: width / 2

                    color: "#07151C"
                    border.color: "#42E8FF"
                    border.width: 2

                    Text {
                        anchors.centerIn: parent

                        text: "D"

                        color: "#DDFBFF"

                        font.family: "Hack"
                        font.pixelSize: 38
                        font.bold: true
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom

                    width: 21
                    height: 21
                    radius: width / 2

                    color: "#42E8FF"
                    border.color: "#02070B"
                    border.width: 3
                }
            }

            Text {
                Layout.alignment:
                    Qt.AlignHCenter

                text: "DARIUSZ"

                color: "#F2FDFF"

                font.family: "Hack"
                font.pixelSize: 23
                font.bold: true
                font.letterSpacing: 1.2
            }

            QQC2.TextField {
                id: usernameField

                Layout.fillWidth: true
                Layout.preferredHeight: 45

                text:
                    userModel.lastUser !== ""
                    ? userModel.lastUser
                    : "dariusz"

                placeholderText:
                    "OPERATOR IDENTIFIER"

                color: "#E5FBFF"
                placeholderTextColor: "#587982"

                selectByMouse: true

                font.family: "Hack"
                font.pixelSize: 12

                leftPadding: 16
                rightPadding: 16

                background: Rectangle {
                    color: "#FF071116"
                    border.color:
                        usernameField.activeFocus
                        ? "#42E8FF"
                        : "#497C8990"

                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom

                        width: 3
                        color: "#42E8FF"
                    }
                }

                Keys.onPressed:
                    function(event) {
                        if (
                            event.key === Qt.Key_Return
                            || event.key === Qt.Key_Enter
                        ) {
                            passwordField.forceActiveFocus()
                            event.accepted = true
                        }
                    }
            }

            QQC2.TextField {
                id: passwordField

                Layout.fillWidth: true
                Layout.preferredHeight: 45

                echoMode: TextInput.Password
                passwordCharacter: "●"

                placeholderText:
                    "PASSWORD CREDENTIAL"

                color: "#E5FBFF"
                placeholderTextColor: "#587982"

                selectByMouse: true

                font.family: "Hack"
                font.pixelSize: 12

                leftPadding: 16
                rightPadding: 16

                background: Rectangle {
                    color: "#FF071116"
                    border.color:
                        passwordField.activeFocus
                        ? "#42E8FF"
                        : "#497C8990"

                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom

                        width: 3
                        color: "#42E8FF"
                    }
                }

                Keys.onPressed:
                    function(event) {
                        if (
                            event.key === Qt.Key_Return
                            || event.key === Qt.Key_Enter
                        ) {
                            root.submitLogin()
                            event.accepted = true
                        }
                    }
            }

            // HELM-STYLE: access-gate-controls-v2
            QQC2.ComboBox {
                id: sessionBox

                Layout.fillWidth: true
                Layout.preferredHeight: 38

                model: sessionModel
                textRole: "name"

                currentIndex:
                    sessionModel.lastIndex >= 0
                    ? sessionModel.lastIndex
                    : 0

                font.family: "Hack"
                font.pixelSize: 10

                hoverEnabled: true

                contentItem: Text {
                    leftPadding: 12
                    rightPadding: 38

                    text:
                        String(
                            sessionBox.displayText
                        ).toUpperCase()

                    color: "#D8FBFF"

                    font.family: "Hack"
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 0.4

                    verticalAlignment:
                        Text.AlignVCenter

                    elide:
                        Text.ElideRight
                }

                indicator: Text {
                    x:
                        sessionBox.width
                        - width
                        - 12

                    y:
                        (
                            sessionBox.height
                            - height
                        ) / 2

                    text:
                        sessionBox.popup.visible
                        ? "▲"
                        : "▼"

                    color:
                        sessionBox.hovered
                        || sessionBox.activeFocus
                        ? "#FFFFFF"
                        : "#42E8FF"

                    font.family: "Hack"
                    font.pixelSize: 9
                    font.bold: true
                }

                background: Rectangle {
                    color:
                        sessionBox.popup.visible
                        ? "#0B2632"
                        : (
                            sessionBox.hovered
                            || sessionBox.activeFocus
                            ? "#0A202A"
                            : "#07151D"
                        )

                    border.color: "#42E8FF"

                    border.width:
                        sessionBox.activeFocus
                        ? 2
                        : 1

                    Rectangle {
                        anchors.left:
                            parent.left

                        anchors.top:
                            parent.top

                        anchors.bottom:
                            parent.bottom

                        width: 3
                        color: "#42E8FF"
                    }
                }

                delegate: QQC2.ItemDelegate {
                    id: sessionDelegate

                    width:
                        sessionBox.width

                    height: 34

                    highlighted:
                        sessionBox.highlightedIndex
                        === index

                    hoverEnabled: true

                    contentItem: Text {
                        leftPadding: 10

                        text:
                            String(
                                sessionBox.textAt(index)
                            ).toUpperCase()

                        color:
                            sessionDelegate.highlighted
                            || sessionDelegate.hovered
                            ? "#02070B"
                            : "#D8FBFF"

                        font.family: "Hack"
                        font.pixelSize: 10
                        font.bold: true

                        verticalAlignment:
                            Text.AlignVCenter

                        elide:
                            Text.ElideRight
                    }

                    background: Rectangle {
                        color:
                            sessionDelegate.highlighted
                            || sessionDelegate.hovered
                            ? "#42E8FF"
                            : "#07151D"

                        border.color:
                            sessionDelegate.highlighted
                            || sessionDelegate.hovered
                            ? "#B8F7FF"
                            : "#16424D"

                        border.width: 1
                    }
                }

                popup: QQC2.Popup {
                    y:
                        sessionBox.height + 2

                    width:
                        sessionBox.width

                    implicitHeight:
                        Math.min(
                            contentItem.implicitHeight,
                            180
                        )

                    padding: 2

                    contentItem: ListView {
                        clip: true

                        implicitHeight:
                            contentHeight

                        model:
                            sessionBox.popup.visible
                            ? sessionBox.delegateModel
                            : null

                        currentIndex:
                            sessionBox.highlightedIndex

                        highlightMoveDuration: 0
                    }

                    background: Rectangle {
                        color: "#050D12"

                        border.color:
                            "#42E8FF"

                        border.width: 1
                    }
                }
            }

            QQC2.Button {
                id: loginButton

                Layout.fillWidth: true
                Layout.preferredHeight: 47

                enabled:
                    !root.authenticating

                hoverEnabled: true

                onClicked:
                    root.submitLogin()

                contentItem: Text {
                    text:
                        root.authenticating
                        ? "AUTHENTICATING..."
                        : "AUTHENTICATE"

                    color:
                        loginButton.hovered
                        && loginButton.enabled
                        ? "#02070B"
                        : "#42E8FF"

                    horizontalAlignment:
                        Text.AlignHCenter

                    verticalAlignment:
                        Text.AlignVCenter

                    font.family: "Hack"
                    font.pixelSize: 12
                    font.bold: true
                    font.letterSpacing: 1
                }

                background: Rectangle {
                    color:
                        loginButton.hovered
                        && loginButton.enabled
                        ? "#42E8FF"
                        : "#0C1920"

                    border.color: "#42E8FF"
                    border.width: 1

                    Behavior on color {
                        ColorAnimation {
                            duration: 130
                        }
                    }
                }
            }

            Text {
                id: statusText

                Layout.fillWidth: true

                text:
                    "STATUS: AWAITING OPERATOR"

                color: "#42E8FF"

                horizontalAlignment:
                    Text.AlignHCenter

                font.family: "Hack"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.35

                wrapMode: Text.WordWrap
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        anchors.rightMargin: 38
        anchors.bottomMargin: 132

        width: 318
        height: 104

        color: "#FC02070B"
        border.color: "#5555DDF3"
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 15

            spacing: 5

            Text {
                text: root.currentTime

                color: "#E6FCFF"

                font.family: "Hack"
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 1.4
            }

            Text {
                text:
                    root.currentDate
                    + "  //  SDDM ACCESS GATE"

                color: "#69A5B1"

                font.family: "Hack"
                font.pixelSize: 9
                font.letterSpacing: 0.25
            }

            Text {
                text:
                    root.authenticating
                    ? "STATUS: AUTHENTICATION ACTIVE"
                    : "STATUS: AWAITING OPERATOR"

                color:
                    root.pulseState
                    ? "#42E8FF"
                    : "#268D9D"

                font.family: "Hack"
                font.pixelSize: 10
                font.bold: true
                font.letterSpacing: 0.45

                Behavior on color {
                    ColorAnimation {
                        duration: 450
                    }
                }
            }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        anchors.leftMargin: 38
        anchors.bottomMargin: 48

        spacing: 16

        QQC2.Button {
            id: suspendButton

            visible:
                sddm.canSuspend

            text: "SUSPEND"

            implicitWidth:
                92

            implicitHeight: 34

            padding: 0
            hoverEnabled: true

            onClicked:
                sddm.suspend()

            contentItem: Text {
                text:
                    suspendButton.text

                color:
                    suspendButton.pressed
                    ? "#02070B"
                    : (
                        suspendButton.hovered
                        ? "#FFFFFF"
                        : "#42E8FF"
                    )

                font.family: "Hack"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.8

                horizontalAlignment:
                    Text.AlignHCenter

                verticalAlignment:
                    Text.AlignVCenter
            }

            background: Rectangle {
                color:
                    suspendButton.pressed
                    ? "#42E8FF"
                    : (
                        suspendButton.hovered
                        ? "#0B2834"
                        : "#061219"
                    )

                border.color:
                    suspendButton.hovered
                    ? "#B8F7FF"
                    : "#42E8FF"

                border.width:
                    suspendButton.hovered
                    || suspendButton.activeFocus
                    ? 2
                    : 1

                Rectangle {
                    anchors.left:
                        parent.left

                    anchors.top:
                        parent.top

                    anchors.bottom:
                        parent.bottom

                    width: 3

                    color:
                        suspendButton.pressed
                        ? "#02070B"
                        : "#42E8FF"
                }
            }
        }

        QQC2.Button {
            id: rebootButton

            visible:
                sddm.canReboot

            text: "REBOOT"

            implicitWidth:
                92

            implicitHeight: 34

            padding: 0
            hoverEnabled: true

            onClicked:
                sddm.reboot()

            contentItem: Text {
                text:
                    rebootButton.text

                color:
                    rebootButton.pressed
                    ? "#02070B"
                    : (
                        rebootButton.hovered
                        ? "#FFFFFF"
                        : "#42E8FF"
                    )

                font.family: "Hack"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.8

                horizontalAlignment:
                    Text.AlignHCenter

                verticalAlignment:
                    Text.AlignVCenter
            }

            background: Rectangle {
                color:
                    rebootButton.pressed
                    ? "#42E8FF"
                    : (
                        rebootButton.hovered
                        ? "#0B2834"
                        : "#061219"
                    )

                border.color:
                    rebootButton.hovered
                    ? "#B8F7FF"
                    : "#42E8FF"

                border.width:
                    rebootButton.hovered
                    || rebootButton.activeFocus
                    ? 2
                    : 1

                Rectangle {
                    anchors.left:
                        parent.left

                    anchors.top:
                        parent.top

                    anchors.bottom:
                        parent.bottom

                    width: 3

                    color:
                        rebootButton.pressed
                        ? "#02070B"
                        : "#42E8FF"
                }
            }
        }

        QQC2.Button {
            id: shutdownButton

            visible:
                sddm.canPowerOff

            text: "SHUTDOWN"

            implicitWidth:
                112

            implicitHeight: 34

            padding: 0
            hoverEnabled: true

            onClicked:
                sddm.powerOff()

            contentItem: Text {
                text:
                    shutdownButton.text

                color:
                    shutdownButton.pressed
                    ? "#02070B"
                    : (
                        shutdownButton.hovered
                        ? "#FFFFFF"
                        : "#42E8FF"
                    )

                font.family: "Hack"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.8

                horizontalAlignment:
                    Text.AlignHCenter

                verticalAlignment:
                    Text.AlignVCenter
            }

            background: Rectangle {
                color:
                    shutdownButton.pressed
                    ? "#42E8FF"
                    : (
                        shutdownButton.hovered
                        ? "#0B2834"
                        : "#061219"
                    )

                border.color:
                    shutdownButton.hovered
                    ? "#B8F7FF"
                    : "#42E8FF"

                border.width:
                    shutdownButton.hovered
                    || shutdownButton.activeFocus
                    ? 2
                    : 1

                Rectangle {
                    anchors.left:
                        parent.left

                    anchors.top:
                        parent.top

                    anchors.bottom:
                        parent.bottom

                    width: 3

                    color:
                        shutdownButton.pressed
                        ? "#02070B"
                        : "#42E8FF"
                }
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        anchors.leftMargin: 38
        anchors.bottomMargin: 32

        width: 180
        height: 2

        color: "#42E8FF"
    }

    Text {
        anchors.horizontalCenter:
            parent.horizontalCenter

        anchors.bottom:
            parent.bottom

        anchors.bottomMargin: 22

        text:
            "HELM CYBERDECK MOBILE"
            + "  //  NATIVE SDDM AUTHENTICATION"

        color: "#42636B"

        font.family: "Hack"
        font.pixelSize: 9
        font.letterSpacing: 0.4
    }
}
