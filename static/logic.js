document.addEventListener('DOMContentLoaded', function() {
    let audioPlayer = new Audio();
    let isPlaying = false;

    document.getElementById('play-pause-btn').addEventListener('click', function() {
        if (isPlaying) {
            audioPlayer.pause();
            this.innerHTML = '<i class="fas fa-play"></i>';
        } else {
            audioPlayer.play();
            this.innerHTML = '<i class="fas fa-pause"></i>';
        }
        isPlaying = !isPlaying;
    });

    document.getElementById('prev-btn').addEventListener('click', function() {
        console.log('Reproducir pista anterior');
    });

    document.getElementById('next-btn').addEventListener('click', function() {
        console.log('Reproducir siguiente pista');
    });

    audioPlayer.addEventListener('timeupdate', function() {
        const currentTime = audioPlayer.currentTime;
        const duration = audioPlayer.duration;
        
        document.getElementById('current-time').textContent = formatTime(currentTime);
        document.getElementById('progress-bar').style.width = (currentTime / duration * 100) + '%';
    });

    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        seconds = Math.floor(seconds % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
});
