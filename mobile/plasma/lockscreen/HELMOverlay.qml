import QtQuick

Item {
    id: root

    anchors.fill: parent
    z: 10000

    property string currentTime: ""
    property string currentDate: ""

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

    Component.onCompleted: updateClock()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.updateClock()
    }

    Rectangle {
        anchors.fill: parent

        color: "transparent"
        border.color: "#2242E8FF"
        border.width: 1
    }

    Rectangle {
        id: securityPanel

        anchors.left: parent.left
        anchors.top: parent.top

        anchors.leftMargin: 38
        anchors.topMargin: 38

        width: Math.min(
            570,
            parent.width * 0.43
        )

        height: 154

        color: "#FF02070B"
        border.color: "#42E8FF"
        border.width: 1
        radius: 0

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
            color: "#5542E8FF"
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
                text: "HELM MOBILE // SECURITY LOCK"

                color: "#42E8FF"

                font.family: "Hack"
                font.pixelSize: 18
                font.bold: true
                font.letterSpacing: 1.2
            }

            Text {
                text: "CYBERDECK-LAPTOP  ·  FIELD NODE 01"

                color: "#D7F9FF"

                font.family: "Hack"
                font.pixelSize: 12
                font.bold: true
                font.letterSpacing: 0.7
            }

            Text {
                text: "OPERATOR DARIUSZ  //  AUTHENTICATION REQUIRED"

                color: "#78A8B3"

                font.family: "Hack"
                font.pixelSize: 11
                font.letterSpacing: 0.35
            }

            Text {
                text: "SESSION SEALED  ·  LOCAL CREDENTIAL CHANNEL"

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
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        anchors.rightMargin: 38
        anchors.bottomMargin: 132

        width: 295
        height: 92

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
                    + "  //  WAYLAND SECURE SESSION"

                color: "#69A5B1"

                font.family: "Hack"
                font.pixelSize: 10
                font.letterSpacing: 0.35
            }

            Text {
                text: "STATUS: AWAITING OPERATOR"

                color: "#42E8FF"

                font.family: "Hack"
                font.pixelSize: 10
                font.bold: true
                font.letterSpacing: 0.45
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        anchors.leftMargin: 38
        anchors.bottomMargin: 38

        width: 180
        height: 2

        color: "#42E8FF"
    }
}
