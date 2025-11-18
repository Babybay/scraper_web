import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity
} from 'react-native';
import axios from 'axios';

const API_BASE = 'http://192.168.1.8:5000';

export default function App() {
  const [destination, setDestination] = useState('Jakarta');
  const [hotels, setHotels] = useState([]);
  const [caption, setCaption] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentAction, setCurrentAction] = useState('');

  const apiRequest = async (endpoint, data = {}) => {
    try {
      const response = await axios.post(`${API_BASE}${endpoint}`, data, {
        timeout: 60000,
        headers: { 'Content-Type': 'application/json' }
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const handleScrapeHotels = async () => {
    setLoading(true);
    setCurrentAction('scraping');
    setHotels([]);
    setCaption('');

    try {
      const result = await apiRequest('/scrape', { destination });
      if (result.success) {
        setHotels(result.hotels);
        Alert.alert('Success', `Found ${result.count} hotels`);
      } else {
        Alert.alert('Error', result.error);
      }
    } catch (error) {
      Alert.alert('Error', 'Request failed');
    } finally {
      setLoading(false);
      setCurrentAction('');
    }
  };

  const handleGenerateCaption = async () => {
    if (hotels.length === 0) {
      Alert.alert('Info', 'Scrape hotels first');
      return;
    }

    setLoading(true);
    setCurrentAction('generating');
    setCaption('');

    try {
      const result = await apiRequest('/generate', { destination });
      if (result.success) {
        setCaption(result.content);
        Alert.alert('Success', 'Caption generated');
      } else {
        Alert.alert('Error', result.error);
      }
    } catch (error) {
      Alert.alert('Error', 'Generation failed');
    } finally {
      setLoading(false);
      setCurrentAction('');
    }
  };

  const handlePublish = async () => {
    if (hotels.length === 0) {
      Alert.alert('Info', 'Scrape hotels first');
      return;
    }

    setLoading(true);
    setCurrentAction('publishing');

    try {
      const result = await apiRequest('/publish', { destination });
      if (result.success) {
        Alert.alert('Success', 'Published');
      } else {
        Alert.alert('Error', result.error);
      }
    } catch (error) {
      Alert.alert('Error', 'Publish failed');
    } finally {
      setLoading(false);
      setCurrentAction('');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Hotel Scraper</Text>
        <Text style={styles.subtitle}>Traveloka • AI • Social Media</Text>
      </View>

      <View style={styles.section}>
        <TextInput
          style={styles.input}
          placeholder="Destination (e.g., Jakarta, Bali)"
          value={destination}
          onChangeText={setDestination}
        />

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleScrapeHotels}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading && currentAction === 'scraping' ? 'Scraping...' : 'Scrape Hotels'}
          </Text>
        </TouchableOpacity>
      </View>

      {hotels.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Hotels ({hotels.length})</Text>
          {hotels.slice(0, 3).map((hotel, index) => (
            <View key={index} style={styles.hotelCard}>
              <Text style={styles.hotelName}>{hotel.name}</Text>
              {hotel.price && <Text style={styles.hotelPrice}>{hotel.price}</Text>}
            </View>
          ))}
        </View>
      )}

      <View style={styles.section}>
        <TouchableOpacity
          style={[styles.button, (loading || hotels.length === 0) && styles.buttonDisabled]}
          onPress={handleGenerateCaption}
          disabled={loading || hotels.length === 0}
        >
          <Text style={styles.buttonText}>
            {loading && currentAction === 'generating' ? 'Generating...' : 'Generate Caption'}
          </Text>
        </TouchableOpacity>

        {caption ? (
          <View style={styles.captionBox}>
            <Text style={styles.captionText}>{caption}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          style={[styles.publishButton, (loading || hotels.length === 0) && styles.buttonDisabled]}
          onPress={handlePublish}
          disabled={loading || hotels.length === 0}
        >
          <Text style={styles.publishButtonText}>
            {loading && currentAction === 'publishing' ? 'Publishing...' : 'Publish Content'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  section: {
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#4F46E5',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 8,
  },
  buttonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  hotelCard: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  hotelName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  hotelPrice: {
    color: '#059669',
    fontSize: 14,
  },
  captionBox: {
    backgroundColor: '#f0f9ff',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#0EA5E9',
  },
  captionText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
  },
  publishButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 12,
  },
  publishButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});