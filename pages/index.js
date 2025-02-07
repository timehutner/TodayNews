import React from 'react';
import styles from '../styles/Home.module.css'; // CSS 모듈 임포트 경로 수정

const Home = () => {
    // 임시 데이터
    const tempNews = [
        { id: 1, title: '첫 번째 카드 뉴스', description: '첫 번째 카드 뉴스의 설명입니다.', category: '사진' },
        { id: 2, title: '두 번째 카드 뉴스', description: '두 번째 카드 뉴스의 설명입니다.', category: '모험' },
    ];

    const headerStyle = {
        backgroundImage: `url('https://cdn.pixabay.com/photo/2022/06/30/02/00/mountains-7292778_1280.jpg')`,
        // ... 다른 스타일 속성 ...
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1 className={styles.title}>카드 뉴스</h1>
                <p>우리는 이야기를 찾기 위해 세상을 여행합니다. 함께 가요!</p>
                <button className={styles.viewPosts}>최신 게시물 보기</button>
            </header>
            <div className={styles.cardContainer}>
                {tempNews.map((item) => ( // 임시 데이터에서 카드 표시
                    <div key={item.id} className={styles.card}>
                        <div className={styles.category}>{item.category}</div>
                        <h2>{item.title}</h2>
                        <p>{item.description}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Home;
